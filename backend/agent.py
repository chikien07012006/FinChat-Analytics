import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.chart import build_ml_chart
from backend.llm import OpenAIService
from backend.tools.ml_tools import MLToolService
from backend.tools.text2sql import Text2SQLService


@dataclass(frozen=True)
class RouteDecision:
    route: str
    tool_name: str
    k: int = 5


class RuleBasedRouter:
    def route(self, message: str) -> RouteDecision:
        normalized = message.lower()
        k = self._extract_k(normalized)

        if any(keyword in normalized for keyword in ["clv", "customer lifetime value", "upsell"]):
            return RouteDecision(route="ml", tool_name="calculate_clv_top_k", k=k)
        if any(keyword in normalized for keyword in ["survival", "time to churn", "days remaining", "remaining to churn"]):
            return RouteDecision(route="ml", tool_name="survival_analysis_top_k", k=k)
        if any(keyword in normalized for keyword in ["causal", "cause of churn", "driver of churn", "lingam"]):
            return RouteDecision(route="ml", tool_name="discover_churn_factors", k=k)
        if any(keyword in normalized for keyword in ["churn", "churn risk", "churn probability"]):
            return RouteDecision(route="ml", tool_name="churn_classification_top_k", k=k)
        if any(keyword in normalized for keyword in ["uplift", "promotion impact", "treatment effect", "incremental impact"]):
            return RouteDecision(route="ml", tool_name="uplift_modeling_positive", k=k)
        return RouteDecision(route="sql", tool_name="text2sql", k=k)

    @staticmethod
    def _extract_k(message: str) -> int:
        match = re.search(r"\btop\s+(\d+)\b", message)
        if match:
            return max(1, min(int(match.group(1)), 50))
        match = re.search(r"\b(\d+)\s+(customers|customer|khach hang)\b", message)
        if match:
            return max(1, min(int(match.group(1)), 50))
        return 5


class HybridRouter:
    VALID_ACTIONS = {
        "chat",
        "text2sql",
        "calculate_clv_top_k",
        "survival_analysis_top_k",
        "churn_classification_top_k",
        "uplift_modeling_positive",
        "discover_churn_factors",
    }

    def __init__(self, llm: OpenAIService) -> None:
        self.llm = llm
        self.fallback_router = RuleBasedRouter()

    def route(self, message: str) -> RouteDecision:
        fallback = self.fallback_router.route(message)

        if self._looks_like_smalltalk(message):
            return RouteDecision(route="chat", tool_name="chat")

        if not self.llm.available:
            return fallback

        try:
            decision = self.llm.classify_route(message)
            action = str(decision.get("action", "")).strip()
            k = max(1, min(int(decision.get("k", fallback.k)), 50))
        except Exception:
            return fallback

        if action not in self.VALID_ACTIONS:
            return fallback

        if action == "chat":
            return RouteDecision(route="chat", tool_name="chat")
        if action == "text2sql":
            return RouteDecision(route="sql", tool_name="text2sql", k=k)
        return RouteDecision(route="ml", tool_name=action, k=k)

    @staticmethod
    def _looks_like_smalltalk(message: str) -> bool:
        normalized = message.strip().lower()
        smalltalk_tokens = {
            "hi",
            "hello",
            "hey",
            "yo",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "oke",
            "good morning",
            "good afternoon",
            "good evening",
            "xin chao",
            "chao",
            "helo",
            "help",
        }
        return normalized in smalltalk_tokens


class AnalyticsAgent:
    def __init__(self) -> None:
        self.llm = OpenAIService()
        self.router = HybridRouter(self.llm)
        self.ml_tools = MLToolService()
        self.text2sql = Text2SQLService()

    def handle(self, message: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        decision = self.router.route(message)
        charts = []
        sql = None
        data: Any = None
        metadata: Dict[str, Any] = {}

        if decision.route == "chat":
            answer = self.llm.generate_general_answer(message)
        elif decision.route == "sql":
            sql_result = self.text2sql.query(question=message, tenant_id=tenant_id)
            data = sql_result["rows"]
            sql = sql_result["sql"]
            metadata = {
                "columns": sql_result["columns"],
                "row_count": sql_result["row_count"],
            }
            answer = self.llm.generate_final_answer(
                question=message,
                route=decision.route,
                tool_used=decision.tool_name,
                data=data,
                charts_present=False,
                sql=sql,
            )
        else:
            tool_result = self.ml_tools.run(tool_name=decision.tool_name, k=decision.k)
            data = tool_result.data
            charts = build_ml_chart(tool_result.tool_name, data)
            metadata = {"k": decision.k}
            if isinstance(data, dict) and "num_customers_positive_uplift" in data and "num_customers_scored" not in data:
                metadata["summary_type"] = "aggregate"
            answer = self.llm.generate_final_answer(
                question=message,
                route=decision.route,
                tool_used=decision.tool_name,
                data=data,
                charts_present=bool(charts),
                sql=sql,
            )

        return {
            "answer": answer,
            "route": decision.route,
            "tool_used": decision.tool_name,
            "data": data,
            "charts": charts,
            "sql": sql,
            "metadata": metadata,
        }
