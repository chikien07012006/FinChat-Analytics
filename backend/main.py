from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
import random
import logging
import json
import time

from backend.agent import AnalyticsAgent
from backend.config import get_settings
from backend.schemas import ChatRequest, ChatResponse, HealthResponse, KPIResponse, UploadResponse
from data.ingestion_pipeline import get_mysql_engine

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
        engine = get_mysql_engine()
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
def chat(request: ChatRequest) -> ChatResponse:
    try:
        logger.info(f"Processing chat request for tenant_id: {request.tenant_id}")
        result = agent.handle(message=request.message, tenant_id=request.tenant_id or settings.tenant_id)
        return ChatResponse(**result)
    except Exception as exc:
        logger.error(f"Error in chat endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/kpis", response_model=KPIResponse)
def get_kpis() -> KPIResponse:
    # TODO: Replace with actual database queries to calculate real KPIs
    return KPIResponse(
        churn_rate=random.uniform(0.1, 0.25),
        avg_clv=random.uniform(1500, 3000),
        total_customers=random.randint(5000, 10000),
        segment_distribution={
            "Champions": random.randint(1000, 2000),
            "At Risk": random.randint(500, 1500),
            "New Customers": random.randint(800, 1200),
            "Hibernating": random.randint(2000, 4000)
        }
    )


@app.post("/api/upload", response_model=UploadResponse)
def upload_data(file: UploadFile = File(...)) -> UploadResponse:
    # TODO: Implement actual data ingestion pipeline processing for the uploaded file
    return UploadResponse(
        status="success",
        filename=file.filename,
        rows_processed=random.randint(100, 1000)
    )
