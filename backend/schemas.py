from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message from the chatbot UI")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant scope")


class ChartPayload(BaseModel):
    chart_id: str
    title: str
    figure: Dict[str, Any]


class ChatResponse(BaseModel):
    answer: str
    route: str
    tool_used: str
    data: Any
    charts: List[ChartPayload] = Field(default_factory=list)
    sql: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    database: str
    llm_configured: bool


class KPIResponse(BaseModel):
    churn_rate: float
    avg_clv: float
    total_customers: int
    segment_distribution: Dict[str, int]


class UploadResponse(BaseModel):
    status: str
    filename: str
    rows_processed: int
