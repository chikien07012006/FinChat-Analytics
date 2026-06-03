from fastapi import FastAPI, HTTPException

from backend.agent import AnalyticsAgent
from backend.config import get_settings
from backend.schemas import ChatRequest, ChatResponse, HealthResponse
from data.ingestion_pipeline import get_mysql_engine


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
agent = AnalyticsAgent()


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
        result = agent.handle(message=request.message, tenant_id=request.tenant_id or settings.tenant_id)
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
