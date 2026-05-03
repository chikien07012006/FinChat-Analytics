import pandas as pd
import numpy as np
from pathlib import Path
import logging
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

class TopKArgsSchema(BaseModel):
    k: int

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
    df["expected_survival"] = expected_survival
    df["days_remaining_to_churn"] = (
        df["expected_survival"] - df["duration"]
    ).where(df["churned"] == 0, 0).clip(lower=0)

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

    X = df.drop(columns=['churned'])
    y = df['churned']

    clf = RandomForestClassifier()
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
