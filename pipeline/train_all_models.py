import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from langchain_core.tools import Tool
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifelines import CoxPHFitter
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from typing import List, Dict, Any
from .feature_engineering import run_feature_engineering
from pydantic.v1 import BaseModel
from causallearn.search.FCMBased.lingam import DirectLiNGAM
from sklearn.preprocessing import StandardScaler

class TopKArgsSchema(BaseModel):
    k: int


def _prepare_numeric_training_frame(df: pd.DataFrame, target_col: str) -> tuple[pd.DataFrame, pd.Series]:
    feature_df = df.drop(columns=[target_col]).copy()

    datetime_cols = feature_df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns
    if len(datetime_cols) > 0:
        feature_df = feature_df.drop(columns=list(datetime_cols))

    for col in feature_df.columns:
        if feature_df[col].dtype == 'object':
            unique_ratio = feature_df[col].nunique(dropna=False) / max(len(feature_df), 1)
            if col.endswith('_id') or unique_ratio > 0.5:
                feature_df = feature_df.drop(columns=[col])
            else:
                feature_df[col] = feature_df[col].fillna('unknown')

    feature_df = pd.get_dummies(feature_df, drop_first=False)
    feature_df = feature_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    return feature_df, df[target_col]

# ---------- Calculate CLV: Top K customers for upsell ----------
def calculate_clv_top_k(k: int) -> List[Dict[str, Any]]:
    df = run_feature_engineering()

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    ggf = GammaGammaFitter(penalizer_coef=0.01)

    bgf.fit(df['frequency'], df['recency_months'], df['T_months'])
    ggf.fit(df['frequency'], df['monetary_value'])

    clv = ggf.customer_lifetime_value(
        bgf,
        df['frequency'],
        df['recency_months'],
        df['T_months'],
        df['monetary_value'],
        time=12
    )

    df['clv'] = clv

    top_k = df[['customer_id', 'clv']].sort_values(by='clv', ascending=False).head(k)

    return top_k.to_dict(orient='records')

calculate_clv_tool = Tool.from_function(
    name="calculate_clv_top_k",
    description="Calculate Customer Lifetime Value (CLV) and get top K customers for upsell.",
    func=calculate_clv_top_k,
    args_schema=TopKArgsSchema
)

# ---------- Survival Analysis: Time to churn for top K risky customers ----------
def survival_analysis_top_k(k: int) -> List[Dict[str, Any]]:
    df = run_feature_engineering()

    covariates = [
        "recency_days", "frequency", "monetary_value", "num_promotions",
        "active_days", "avg_days_between"
    ]
    
    cph = CoxPHFitter()
    cph.fit(df[["duration", "churned"] + covariates], duration_col="duration", event_col="churned")

    expected_survival = cph.predict_expectation(df[covariates])
    df["expected_survival"] = expected_survival # thời gian sống dự kiến từ khi bắt đầu tương tác
    df["days_remaining_to_churn"] = (
        df["expected_survival"] - df["duration"]
    ).where(df["churned"] == 0, 0).clip(lower=0) # chỉ gán khi churned = 0, còn churned = 1 thì để 0

    # Customers with shortest days remaining are highest churn risk
    top_k = df[['customer_id', 'days_remaining_to_churn']].sort_values(
        by='days_remaining_to_churn'
    ).head(k)

    return top_k.to_dict(orient='records')

survival_analysis_tool = Tool.from_function(
    name="survival_analysis_top_k",
    description="Estimate remaining time to churn for top K highest-risk customers.",
    func=survival_analysis_top_k,
    args_schema=TopKArgsSchema
)


# ---------- Churn Classification: Top K customers with highest churn probability ----------
def churn_classification_top_k(k: int) -> List[Dict[str, Any]]:
    df = run_feature_engineering()

    X, y = _prepare_numeric_training_frame(df, target_col='churned')

    clf = RandomForestClassifier(random_state=42)
    clf.fit(X, y)

    churn_probs = clf.predict_proba(X)[:, 1]
    df['churn_probability'] = churn_probs

    top_k = df[['customer_id', 'churn_probability']].sort_values(by='churn_probability', ascending=False).head(k)

    return top_k.to_dict(orient='records')

churn_classification_tool = Tool.from_function(
    name="churn_classification_top_k",
    description="Predict churn probability and get top K customers with highest churn risk.",
    func=churn_classification_top_k,
    args_schema=TopKArgsSchema
)

# ---------- Uplift Modeling: Count customers with positive uplift ----------
def uplift_modeling_positive() -> Dict[str, Any]:
    df = run_feature_engineering()

    feature_columns = [
        "recency_days", "frequency", "monetary_value", "T_months", 
        "recency_months", "recency_over_T", "freq_over_T", "freq_30d", 
        "monetary_30d", "freq_90d", "monetary_90d", "freq_180d", 
        "monetary_180d", "freq_ratio", "monetary_ratio", "avg_days_between", 
        "std_days_between", "avg_tx_value", "max_tx_value", "min_tx_value", 
        "transaction_count_total", "active_days", "active_days_ratio", 
        "num_promotions", "days_since_last_promotion"
    ]
    
    X = df[feature_columns]
    T = df['received_promotion']
    y = df['conversion']

    # T-learner: Train separate models for treated and control groups
    if T.sum() == 0 or (len(T) - T.sum()) == 0:
        return {"num_customers_positive_uplift": 0}

    model_t = RandomForestClassifier(random_state=42)
    model_c = RandomForestClassifier(random_state=42)

    model_t.fit(X[T == 1], y[T == 1])
    model_c.fit(X[T == 0], y[T == 0])

    # Predict uplift as the difference in conversion probability
    p_t = model_t.predict_proba(X)[:, 1]
    p_c = model_c.predict_proba(X)[:, 1]

    df['uplift'] = p_t - p_c
    num_positive_uplift = (df['uplift'] > 0).sum()

    return {"num_customers_positive_uplift": int(num_positive_uplift)}

uplift_modeling_tool = Tool.from_function(
    name="uplift_modeling_positive",
    description="Count how many customers have positive uplift if given a promotion.",
    func=uplift_modeling_positive,
    args_schema=BaseModel  # No args needed
)

# ---------- Discover potential causal factors for churn ----------
def discover_churn_factors() -> Dict[str, Any]:
    df = run_feature_engineering()
    demographic_cols = ["age", "gender", "city", "segment_initial", "num_promotions"]
    extra_cols = [col for col in df.columns if col.startswith((
        "gender_", "education_level_", "marital_status_", 
        "profession_", "customer_segment_"
    ))]
    
    available_cols = [c for c in demographic_cols + extra_cols if c in df.columns]
    cols_to_use = available_cols + ["churned"]

    data = df[cols_to_use].copy()

    # Encode Categorical / Ordinal features
    if 'segment_initial' in data.columns:
        segment_map = {'Mass': 0, 'Premium': 1, 'VIP': 2}
        data['segment_initial'] = data['segment_initial'].map(segment_map).fillna(0)

    if 'gender' in data.columns:
        data['gender'] = data['gender'].map({'Male': 0, 'Female': 1}).fillna(-1)

    if 'city' in data.columns:
        data['city'] = pd.Categorical(data['city']).codes

    data = data.apply(pd.to_numeric, errors='coerce').dropna()

    if data.empty:
        return {"churn_factors": []}

    # Scaling
    scaler = StandardScaler()
    features = [c for c in data.columns if c != "churned"]
    data_scaled = pd.DataFrame(scaler.fit_transform(data[features]), columns=features, index=data.index)
    data_scaled["churned"] = data["churned"]
    
    # Structural Causal Discovery using DirectLiNGAM
    model = DirectLiNGAM()
    model.fit(data_scaled)
    
    adj = model.adjacency_matrix_
    
    try:
        churned_idx = list(data_scaled.columns).index("churned")
    except ValueError:
        return {"churn_factors": []}

    causal_factors = []
    for j in range(len(features) + 1):
        weight = adj[churned_idx, j]
        if j != churned_idx and abs(weight) > 0.02:
            feature_name = data_scaled.columns[j]
            causal_factors.append({
                "feature": feature_name,
                "weight": round(float(weight), 4)
            })

    # Sort factors by absolute weight
    causal_factors = sorted(causal_factors, key=lambda x: abs(x['weight']), reverse=True)
    
    return {"churn_factors": causal_factors}

discover_churn_factors_tool = Tool.from_function(
    name="discover_churn_factors",
    description="Discover factors that may causally influence churn.",
    func=discover_churn_factors,
    args_schema=BaseModel  
)
