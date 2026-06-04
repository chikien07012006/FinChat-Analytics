import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

import mlflow
import mlflow.pyfunc
import mlflow.sklearn
import numpy as np
import pandas as pd
from causallearn.search.FCMBased.lingam import DirectLiNGAM
from lifelines import CoxPHFitter
from lifetimes import BetaGeoFitter, GammaGammaFitter
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from data.ingestion_pipeline import get_db_engine
from pipeline.feature_engineering import run_feature_engineering

logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

RANDOM_STATE = 42

CHURN_EXCLUDE_COLUMNS = {
    "customer_id",
    "tenant_id",
    "first_tx",
    "last_tx",
    "snapshot_date",
    "feature_version",
    "promotion_types",
    "last_promotion_date",
    "churn",
    "churned",
}

SURVIVAL_COVARIATES = [
    "recency_days",
    "frequency",
    "monetary_value",
    "num_promotions",
    "active_days",
    "avg_days_between",
]

UPLIFT_FEATURE_COLUMNS = [
    "recency_days",
    "frequency",
    "monetary_value",
    "T_months",
    "recency_months",
    "recency_over_T",
    "freq_over_T",
    "freq_30d",
    "monetary_30d",
    "freq_90d",
    "monetary_90d",
    "freq_180d",
    "monetary_180d",
    "freq_ratio",
    "monetary_ratio",
    "avg_days_between",
    "std_days_between",
    "avg_tx_value",
    "max_tx_value",
    "min_tx_value",
    "transaction_count_total",
    "active_days",
    "active_days_ratio",
    "num_promotions",
    "days_since_last_promotion",
]


class SurvivalPyFuncModel(mlflow.pyfunc.PythonModel):
    def __init__(self, model: CoxPHFitter, feature_columns: list[str]):
        self.model = model
        self.feature_columns = feature_columns

    def predict(self, context: Any, model_input: pd.DataFrame) -> pd.Series:
        return self.model.predict_expectation(model_input[self.feature_columns])


class CLVPyFuncModel(mlflow.pyfunc.PythonModel):
    def __init__(
        self,
        bgf: BetaGeoFitter,
        ggf: GammaGammaFitter,
        feature_columns: list[str],
        prediction_months: int = 12,
    ):
        self.bgf = bgf
        self.ggf = ggf
        self.feature_columns = feature_columns
        self.prediction_months = prediction_months

    def predict(self, context: Any, model_input: pd.DataFrame) -> pd.Series:
        frame = model_input[self.feature_columns]
        return self.ggf.customer_lifetime_value(
            self.bgf,
            frame["frequency"],
            frame["recency_months"],
            frame["T_months"],
            frame["monetary_value"],
            time=self.prediction_months,
        )


class UpliftPyFuncModel(mlflow.pyfunc.PythonModel):
    def __init__(
        self,
        treatment_model: Pipeline,
        control_model: Pipeline,
        feature_columns: list[str],
    ):
        self.treatment_model = treatment_model
        self.control_model = control_model
        self.feature_columns = feature_columns

    def predict(self, context: Any, model_input: pd.DataFrame) -> pd.Series:
        frame = model_input[self.feature_columns]
        p_treatment = self.treatment_model.predict_proba(frame)[:, 1]
        p_control = self.control_model.predict_proba(frame)[:, 1]
        return pd.Series(p_treatment - p_control, index=model_input.index)


def configure_mlflow() -> None:
    mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name(Config.MLFLOW_EXPERIMENT_NAME)
    if experiment is None:
        client.create_experiment(
            Config.MLFLOW_EXPERIMENT_NAME,
            artifact_location=Config.MLFLOW_ARTIFACT_ROOT,
        )
    mlflow.set_experiment(Config.MLFLOW_EXPERIMENT_NAME)


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _log_dataframe(df: pd.DataFrame, path: Path, artifact_path: str) -> None:
    df.to_csv(path, index=False)
    mlflow.log_artifact(str(path), artifact_path=artifact_path)


def _get_registered_version(model_name: str, run_id: str) -> str:
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions(f"name = '{model_name}'")
    matching_versions = [version for version in versions if version.run_id == run_id]
    if not matching_versions:
        return "unregistered"
    return max(matching_versions, key=lambda version: int(version.version)).version


def build_classifier_pipeline(df: pd.DataFrame, feature_columns: list[str]) -> Pipeline:
    categorical_columns = [
        column
        for column in feature_columns
        if df[column].dtype == "object" or str(df[column].dtype) == "category"
    ]
    numeric_columns = [column for column in feature_columns if column not in categorical_columns]

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median"), numeric_columns),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            ),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=300,
                    min_samples_leaf=5,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_churn_model(df: pd.DataFrame, artifact_dir: Path) -> tuple[pd.Series, str]:
    feature_columns = [
        column
        for column in df.columns
        if column not in CHURN_EXCLUDE_COLUMNS and column != "duration"
    ]
    X = df[feature_columns]
    y = df["churned"].astype(int)

    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=RANDOM_STATE,
        stratify=stratify,
    )

    pipeline = build_classifier_pipeline(df, feature_columns)
    pipeline.fit(X_train, y_train)

    probabilities = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probabilities) if y_test.nunique() > 1 else np.nan
    report = classification_report(y_test, pipeline.predict(X_test), output_dict=True)

    full_probabilities = pd.Series(
        pipeline.predict_proba(X)[:, 1],
        index=df.index,
        name="churn_probability",
    )

    with mlflow.start_run(run_name="churn_classifier") as run:
        mlflow.log_params(
            {
                "model_type": "RandomForestClassifier",
                "n_estimators": 300,
                "min_samples_leaf": 5,
                "test_size": 0.30,
                "feature_count": len(feature_columns),
            }
        )
        mlflow.log_metric("roc_auc", float(auc))
        _write_json(artifact_dir / "churn_feature_columns.json", feature_columns)
        _write_json(artifact_dir / "churn_classification_report.json", report)
        mlflow.log_artifact(str(artifact_dir / "churn_feature_columns.json"), artifact_path="features")
        mlflow.log_artifact(str(artifact_dir / "churn_classification_report.json"), artifact_path="reports")
        mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
            registered_model_name=Config.MLFLOW_CHURN_MODEL_NAME,
        )

    version = _get_registered_version(Config.MLFLOW_CHURN_MODEL_NAME, run.info.run_id)
    model_version = f"{Config.MLFLOW_CHURN_MODEL_NAME}/v{version}"
    return full_probabilities, model_version


def train_survival_model(df: pd.DataFrame, artifact_dir: Path) -> tuple[pd.Series, str]:
    survival_df = df[["duration", "churned", *SURVIVAL_COVARIATES]].copy()
    survival_df = survival_df.replace([np.inf, -np.inf], np.nan).dropna()

    model = CoxPHFitter()
    model.fit(survival_df, duration_col="duration", event_col="churned")

    predictions = pd.Series(0.0, index=df.index, name="time_to_churn_days")
    expected_survival = model.predict_expectation(df[SURVIVAL_COVARIATES])
    predictions.loc[df.index] = (
        expected_survival - df["duration"]
    ).where(df["churned"] == 0, 0).clip(lower=0)

    with mlflow.start_run(run_name="survival_coxph") as run:
        mlflow.log_params(
            {
                "model_type": "CoxPHFitter",
                "feature_count": len(SURVIVAL_COVARIATES),
                "duration_col": "duration",
                "event_col": "churned",
            }
        )
        mlflow.log_metric("concordance_index", float(model.concordance_index_))
        _write_json(artifact_dir / "survival_feature_columns.json", SURVIVAL_COVARIATES)
        model.summary.reset_index().to_csv(artifact_dir / "survival_summary.csv", index=False)
        mlflow.log_artifact(str(artifact_dir / "survival_feature_columns.json"), artifact_path="features")
        mlflow.log_artifact(str(artifact_dir / "survival_summary.csv"), artifact_path="reports")
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=SurvivalPyFuncModel(model, SURVIVAL_COVARIATES),
            registered_model_name=Config.MLFLOW_SURVIVAL_MODEL_NAME,
        )

    version = _get_registered_version(Config.MLFLOW_SURVIVAL_MODEL_NAME, run.info.run_id)
    model_version = f"{Config.MLFLOW_SURVIVAL_MODEL_NAME}/v{version}"
    return predictions, model_version


def train_clv_model(df: pd.DataFrame, artifact_dir: Path) -> tuple[pd.Series, str]:
    clv_columns = ["customer_id", "frequency", "recency_months", "T_months", "monetary_value"]
    clv_df = df[clv_columns].copy()
    clv_df = clv_df.replace([np.inf, -np.inf], np.nan).dropna()
    clv_df = clv_df[
        (clv_df["frequency"] > 0)
        & (clv_df["recency_months"] >= 0)
        & (clv_df["T_months"] > 0)
        & (clv_df["monetary_value"] > 0)
    ]

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    bgf.fit(clv_df["frequency"], clv_df["recency_months"], clv_df["T_months"])
    ggf.fit(clv_df["frequency"], clv_df["monetary_value"])

    clv_values = ggf.customer_lifetime_value(
        bgf,
        clv_df["frequency"],
        clv_df["recency_months"],
        clv_df["T_months"],
        clv_df["monetary_value"],
        time=12,
    )
    clv_predictions = pd.Series(0.0, index=df.index, name="clv_12m")
    clv_predictions.loc[clv_df.index] = clv_values.clip(lower=0)

    top_clv = (
        pd.DataFrame({"customer_id": clv_df["customer_id"], "clv_12m": clv_values})
        .sort_values("clv_12m", ascending=False)
        .head(100)
    )

    with mlflow.start_run(run_name="clv_bgnbd_gamma_gamma") as run:
        mlflow.log_params(
            {
                "model_type": "BetaGeoFitter+GammaGammaFitter",
                "penalizer_coef": 0.01,
                "prediction_months": 12,
                "training_rows": len(clv_df),
            }
        )
        mlflow.log_metric("mean_clv_12m", float(clv_values.mean()))
        mlflow.log_metric("median_clv_12m", float(clv_values.median()))
        _write_json(artifact_dir / "clv_feature_columns.json", clv_columns[1:])
        _log_dataframe(top_clv, artifact_dir / "top_clv_customers.csv", artifact_path="reports")
        mlflow.log_artifact(str(artifact_dir / "clv_feature_columns.json"), artifact_path="features")
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=CLVPyFuncModel(bgf, ggf, clv_columns[1:]),
            registered_model_name=Config.MLFLOW_CLV_MODEL_NAME,
        )

    version = _get_registered_version(Config.MLFLOW_CLV_MODEL_NAME, run.info.run_id)
    model_version = f"{Config.MLFLOW_CLV_MODEL_NAME}/v{version}"
    return clv_predictions, model_version


def train_uplift_model(df: pd.DataFrame, artifact_dir: Path) -> tuple[pd.Series, str]:
    uplift_df = df[["customer_id", "received_promotion", "conversion", *UPLIFT_FEATURE_COLUMNS]].copy()
    uplift_df = uplift_df.replace([np.inf, -np.inf], np.nan).dropna()

    treatment = uplift_df["received_promotion"].astype(bool)
    if treatment.sum() == 0 or (~treatment).sum() == 0:
        logger.warning("Skipping uplift model registration: missing treatment or control rows")
        return pd.Series(0.0, index=df.index, name="uplift_score"), "unregistered"

    X = uplift_df[UPLIFT_FEATURE_COLUMNS]
    y = uplift_df["conversion"].astype(int)

    treatment_model = build_classifier_pipeline(uplift_df, UPLIFT_FEATURE_COLUMNS)
    control_model = build_classifier_pipeline(uplift_df, UPLIFT_FEATURE_COLUMNS)
    treatment_model.fit(X[treatment], y[treatment])
    control_model.fit(X[~treatment], y[~treatment])

    uplift_values = pd.Series(
        treatment_model.predict_proba(X)[:, 1] - control_model.predict_proba(X)[:, 1],
        index=uplift_df.index,
        name="uplift_score",
    )
    uplift_predictions = pd.Series(0.0, index=df.index, name="uplift_score")
    uplift_predictions.loc[uplift_df.index] = uplift_values

    uplift_report = pd.DataFrame(
        {
            "customer_id": uplift_df["customer_id"],
            "uplift_score": uplift_values,
            "received_promotion": treatment,
            "conversion": y,
        }
    ).sort_values("uplift_score", ascending=False)

    with mlflow.start_run(run_name="uplift_t_learner") as run:
        mlflow.log_params(
            {
                "model_type": "T-Learner RandomForestClassifier",
                "feature_count": len(UPLIFT_FEATURE_COLUMNS),
                "treatment_rows": int(treatment.sum()),
                "control_rows": int((~treatment).sum()),
            }
        )
        mlflow.log_metric("mean_uplift", float(uplift_values.mean()))
        mlflow.log_metric("positive_uplift_customers", int((uplift_values > 0).sum()))
        _write_json(artifact_dir / "uplift_feature_columns.json", UPLIFT_FEATURE_COLUMNS)
        _log_dataframe(
            uplift_report.head(100),
            artifact_dir / "top_uplift_customers.csv",
            artifact_path="reports",
        )
        mlflow.log_artifact(str(artifact_dir / "uplift_feature_columns.json"), artifact_path="features")
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=UpliftPyFuncModel(treatment_model, control_model, UPLIFT_FEATURE_COLUMNS),
            registered_model_name=Config.MLFLOW_UPLIFT_MODEL_NAME,
        )

    version = _get_registered_version(Config.MLFLOW_UPLIFT_MODEL_NAME, run.info.run_id)
    model_version = f"{Config.MLFLOW_UPLIFT_MODEL_NAME}/v{version}"
    return uplift_predictions, model_version


def log_causal_discovery(df: pd.DataFrame, artifact_dir: Path) -> None:
    demographic_columns = ["age", "gender", "city", "segment_initial", "num_promotions"]
    available_columns = [column for column in demographic_columns if column in df.columns]
    data = df[[*available_columns, "churned"]].copy()

    if "segment_initial" in data.columns:
        data["segment_initial"] = data["segment_initial"].map({"Mass": 0, "Premium": 1, "VIP": 2}).fillna(0)
    if "gender" in data.columns:
        data["gender"] = data["gender"].map({"Male": 0, "Female": 1, "Other": 2}).fillna(-1)
    if "city" in data.columns:
        data["city"] = pd.Categorical(data["city"]).codes

    data = data.apply(pd.to_numeric, errors="coerce").dropna()
    if data.empty:
        logger.warning("Skipping causal discovery: no valid numeric rows")
        return

    features = [column for column in data.columns if column != "churned"]
    scaled = pd.DataFrame(
        StandardScaler().fit_transform(data[features]),
        columns=features,
        index=data.index,
    )
    scaled["churned"] = data["churned"].astype(int)

    model = DirectLiNGAM()
    model.fit(scaled)
    adjacency = model.adjacency_matrix_
    churn_index = list(scaled.columns).index("churned")

    causal_factors = []
    for feature_index, feature_name in enumerate(scaled.columns):
        if feature_name == "churned":
            continue
        weight = adjacency[churn_index, feature_index]
        if abs(weight) > 0.02:
            causal_factors.append({"feature": feature_name, "weight": round(float(weight), 4)})

    causal_factors = sorted(causal_factors, key=lambda item: abs(item["weight"]), reverse=True)

    with mlflow.start_run(run_name="causal_discovery_direct_lingam"):
        mlflow.log_params(
            {
                "model_type": "DirectLiNGAM",
                "feature_count": len(features),
                "threshold_abs_weight": 0.02,
            }
        )
        mlflow.log_metric("causal_factor_count", len(causal_factors))
        _write_json(artifact_dir / "causal_factors.json", causal_factors)
        pd.DataFrame(causal_factors).to_csv(artifact_dir / "causal_factors.csv", index=False)
        mlflow.log_artifact(str(artifact_dir / "causal_factors.json"), artifact_path="reports")
        mlflow.log_artifact(str(artifact_dir / "causal_factors.csv"), artifact_path="reports")


def update_customer_features(
    df: pd.DataFrame,
    predictions: dict[str, pd.Series],
    model_versions: dict[str, str],
) -> None:
    output = pd.DataFrame(
        {
            "customer_id": df["customer_id"],
            "tenant_id": df["tenant_id"],
            "rfm_recency": df["recency_days"].round().astype(int),
            "rfm_frequency": df["frequency"].round().astype(int),
            "rfm_monetary": df["monetary_value"].round(2),
            "clv_12m": predictions["clv_12m"].round(2),
            "churn_probability": predictions["churn_probability"].clip(0, 1).round(4),
            "time_to_churn_days": predictions["time_to_churn_days"].round().astype(int),
            "uplift_score": predictions["uplift_score"].round(4),
        }
    )
    output["scoring_date"] = pd.Timestamp.utcnow().tz_localize(None)
    output["model_version"] = (
        f"churn:{model_versions['churn'].split('/')[-1]};"
        f"surv:{model_versions['survival'].split('/')[-1]};"
        f"clv:{model_versions['clv'].split('/')[-1]};"
        f"uplift:{model_versions['uplift'].split('/')[-1]}"
    )

    temp_table = "tmp_customer_features_mlflow"
    columns = list(output.columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    update_clause = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in columns if column != "customer_id"
    )

    engine = get_db_engine()
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))

    output.to_sql(temp_table, con=engine, if_exists="replace", index=False, chunksize=20_000, method="multi")

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO customer_features ({quoted_columns})
            SELECT {quoted_columns}
            FROM "{temp_table}"
            ON CONFLICT (customer_id) DO UPDATE SET
                {update_clause}
        """))
        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))

    logger.info("Updated customer_features with MLflow model outputs")


def main() -> None:
    configure_mlflow()
    logger.info("Running feature engineering from Supabase")
    features = run_feature_engineering()
    logger.info("Feature matrix shape: %s", features.shape)

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)
        predictions: dict[str, pd.Series] = {}
        model_versions: dict[str, str] = {}

        predictions["churn_probability"], model_versions["churn"] = train_churn_model(features, artifact_dir)
        predictions["time_to_churn_days"], model_versions["survival"] = train_survival_model(features, artifact_dir)
        predictions["clv_12m"], model_versions["clv"] = train_clv_model(features, artifact_dir)
        predictions["uplift_score"], model_versions["uplift"] = train_uplift_model(features, artifact_dir)
        log_causal_discovery(features, artifact_dir)

        update_customer_features(features, predictions, model_versions)

    logger.info("MLflow training completed. Tracking URI: %s", Config.MLFLOW_TRACKING_URI)


if __name__ == "__main__":
    main()
