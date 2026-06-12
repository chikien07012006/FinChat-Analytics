from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FinChat Analytics Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    tenant_id: str = Field(default="BANK001", alias="TENANT_ID")

    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_jwt_secret: Optional[str] = Field(default=None, alias="SUPABASE_JWT_SECRET")

    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")
    sql_result_limit: int = Field(default=100, alias="SQL_RESULT_LIMIT")
    mlflow_tracking_uri: str = Field(default="mlruns", alias="MLFLOW_TRACKING_URI")

    @property
    def sqlalchemy_database_uri(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required. Use the Supabase Postgres SQLAlchemy URL.")
        return self.database_url

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def supabase_auth_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
