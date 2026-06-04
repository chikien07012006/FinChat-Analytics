import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "finchat-analytics")
    MLFLOW_ARTIFACT_ROOT = os.getenv("MLFLOW_ARTIFACT_ROOT", "mlruns")

    MLFLOW_CHURN_MODEL_NAME = os.getenv("MLFLOW_CHURN_MODEL_NAME", "finchat_churn_model")
    MLFLOW_SURVIVAL_MODEL_NAME = os.getenv("MLFLOW_SURVIVAL_MODEL_NAME", "finchat_survival_model")
    MLFLOW_CLV_MODEL_NAME = os.getenv("MLFLOW_CLV_MODEL_NAME", "finchat_clv_model")
    MLFLOW_UPLIFT_MODEL_NAME = os.getenv("MLFLOW_UPLIFT_MODEL_NAME", "finchat_uplift_model")
    
    TENANT_ID = os.getenv("TENANT_ID", "BANK001")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
