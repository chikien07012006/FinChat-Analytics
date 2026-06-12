from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
import logging
import json
import time
from typing import Tuple

import pandas as pd
from sqlalchemy import text

from backend.agent import AnalyticsAgent
from backend.auth import AuthContext, get_current_user
from backend.config import get_settings
from backend.schemas import ChatRequest, ChatResponse, HealthResponse, KPIResponse, UploadResponse
from data.ingestion_pipeline import get_database_engine, ingest_dataframe_to_database

# --- Structured Logging Setup ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("finchat_backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
# --------------------------------


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
agent = AnalyticsAgent()

@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)}
    )

@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    database_status = "healthy"
    try:
        engine = get_database_engine()
        with engine.connect():
            pass
    except Exception:
        database_status = "unhealthy"

    return HealthResponse(
        status="ok" if database_status == "healthy" else "degraded",
        app=settings.app_name,
        version=settings.app_version,
        database=database_status,
        llm_configured=settings.llm_configured,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: AuthContext = Depends(get_current_user)) -> ChatResponse:
    try:
        logger.info(f"Processing chat request for user_id: {current_user.user_id}")
        result = agent.handle(message=request.message, tenant_id=current_user.tenant_id)
        return ChatResponse(**result)
    except Exception as exc:
        logger.error(f"Error in chat endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/kpis", response_model=KPIResponse)
def get_kpis(current_user: AuthContext = Depends(get_current_user)) -> KPIResponse:
    engine = get_database_engine()
    with engine.connect() as conn:
        totals = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_customers,
                    COALESCE(AVG(CASE WHEN churn THEN 1.0 ELSE 0.0 END), 0) AS churn_rate
                FROM customer_data
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": current_user.tenant_id},
        ).mappings().one()
        avg_clv = conn.execute(
            text(
                """
                SELECT COALESCE(AVG(clv_12m), 0) AS avg_clv
                FROM customer_features
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": current_user.tenant_id},
        ).scalar()
        segments = conn.execute(
            text(
                """
                SELECT COALESCE(segment_initial, 'Unknown') AS segment, COUNT(*) AS count
                FROM customer_data
                WHERE tenant_id = :tenant_id
                GROUP BY COALESCE(segment_initial, 'Unknown')
                ORDER BY count DESC
                """
            ),
            {"tenant_id": current_user.tenant_id},
        ).mappings().all()

    return KPIResponse(
        churn_rate=float(totals["churn_rate"] or 0),
        avg_clv=float(avg_clv or 0),
        total_customers=int(totals["total_customers"] or 0),
        segment_distribution={str(row["segment"]): int(row["count"]) for row in segments},
    )


@app.post("/api/upload", response_model=UploadResponse)
def upload_data(
    file: UploadFile = File(...),
    current_user: AuthContext = Depends(get_current_user),
) -> UploadResponse:
    try:
        df = pd.read_csv(file.file)
        table_name, prepared = _prepare_upload_dataframe(df, current_user.tenant_id)
        rows_processed = ingest_dataframe_to_database(prepared, table_name, if_exists="append")
    except Exception as exc:
        logger.error(f"Upload failed for {file.filename}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        status="success",
        filename=file.filename,
        rows_processed=rows_processed,
    )


def _prepare_upload_dataframe(df: pd.DataFrame, tenant_id: str) -> Tuple[str, pd.DataFrame]:
    if df.empty:
        raise ValueError("Uploaded CSV is empty.")

    prepared = df.copy()
    prepared["tenant_id"] = tenant_id

    if "transaction_id" in prepared.columns:
        required = {"transaction_id", "customer_id", "transaction_date", "amount"}
        missing = required - set(prepared.columns)
        if missing:
            raise ValueError(f"Transaction upload is missing columns: {', '.join(sorted(missing))}")
        return "raw_transactions", prepared

    if "customer_id" in prepared.columns:
        required = {"customer_id", "signup_date"}
        missing = required - set(prepared.columns)
        if missing:
            raise ValueError(f"Customer upload is missing columns: {', '.join(sorted(missing))}")
        for column in ["received_promotion", "churn"]:
            if column in prepared.columns:
                prepared[column] = prepared[column].astype(bool)
        return "customer_data", prepared

    raise ValueError("CSV must contain customer_id or transaction_id columns.")
