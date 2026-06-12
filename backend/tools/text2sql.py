import re
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import inspect, text

from backend.config import get_settings
from backend.llm import GeminiService
from data.ingestion_pipeline import get_database_engine


READ_ONLY_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
FORBIDDEN_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|call)\b",
    re.IGNORECASE,
)


class Text2SQLService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = GeminiService()
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = get_database_engine()
        return self._engine

    def query(self, question: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        schema_text = self._build_schema_context()
        sql = self.llm.generate_sql(question=question, schema_text=schema_text, tenant_id=tenant_id)
        sanitized_sql = self._sanitize_sql(sql, tenant_id=tenant_id)
        df = pd.read_sql_query(text(sanitized_sql), self.engine)
        data = df.head(self.settings.sql_result_limit).to_dict(orient="records")
        return {
            "sql": sanitized_sql,
            "columns": list(df.columns),
            "row_count": int(len(df)),
            "rows": data,
        }

    def _build_schema_context(self) -> str:
        inspector = inspect(self.engine)
        schema_lines: List[str] = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_desc = ", ".join(f"{col['name']} {col['type']}" for col in columns)
            schema_lines.append(f"{table_name}: {column_desc}")
        return "\n".join(schema_lines)

    def _sanitize_sql(self, sql: str, tenant_id: Optional[str] = None) -> str:
        cleaned = sql.strip().strip("`").strip()
        cleaned = cleaned.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()

        if ";" in cleaned[:-1]:
            raise ValueError("Only a single SQL statement is allowed.")
        if not READ_ONLY_PATTERN.match(cleaned):
            raise ValueError("Only SELECT queries are allowed.")
        if FORBIDDEN_PATTERN.search(cleaned):
            raise ValueError("Only read-only SQL is allowed.")
        if tenant_id and self._query_touches_tenant_tables(cleaned) and "tenant_id" not in cleaned.lower():
            raise ValueError("Generated SQL must include tenant_id filtering.")

        return cleaned

    @staticmethod
    def _query_touches_tenant_tables(sql: str) -> bool:
        normalized = sql.lower()
        return any(table in normalized for table in ["customer_data", "raw_transactions", "customer_features"])
