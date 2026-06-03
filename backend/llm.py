import json
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.config import get_settings


class OpenAIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

        if self.settings.llm_configured:
            self._client = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0.2,
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def generate_sql(self, question: str, schema_text: str, tenant_id: Optional[str] = None) -> str:
        if not self.available:
            raise RuntimeError("OpenAI is not configured. Add OPENAI_API_KEY to .env before using Text2SQL.")

        tenant_hint = (
            f"Prefer filtering by tenant_id = '{tenant_id}' when the table contains a tenant_id column."
            if tenant_id
            else "Do not assume a tenant filter unless the user explicitly asks for it."
        )

        system_prompt = (
            "You are a careful SQL assistant for MySQL. "
            "Return exactly one SQL statement. Use only SELECT or WITH queries. "
            "Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or multiple statements. "
            "Use only tables and columns present in the provided schema. "
            f"{tenant_hint}"
        )

        human_prompt = (
            f"Schema:\n{schema_text}\n\n"
            f"Question: {question}\n\n"
            "Return SQL only. Do not use markdown fences."
        )

        response = self._client.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        return response.content.strip()

    def classify_route(self, question: str) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("OpenAI is not configured. Add OPENAI_API_KEY to .env before routing with LLM.")

        system_prompt = (
            "You are a routing classifier for an internal banking analytics assistant. "
            "Return valid JSON only. "
            "Available actions are: "
            "`chat`, `text2sql`, `calculate_clv_top_k`, `survival_analysis_top_k`, "
            "`churn_classification_top_k`, `uplift_modeling_positive`, `discover_churn_factors`. "
            "Choose `chat` for greetings, small talk, thanks, help requests, or general conversation that does not need tools. "
            "Choose `text2sql` for straightforward business data questions over raw or feature tables. "
            "Choose an ML action only when the user clearly asks for CLV, churn, survival, uplift, or causal analysis."
        )
        human_prompt = (
            "Return JSON in this exact shape: "
            '{"action":"...", "k": 5, "reason":"..."}\n'
            f"User message: {question}"
        )

        response = self._client.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        content = response.content.strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(content)
        parsed["action"] = str(parsed.get("action", "")).strip()
        parsed["k"] = int(parsed.get("k", 5) or 5)
        return parsed

    def generate_general_answer(self, question: str) -> str:
        if not self.available:
            return "Hello. I can help with business data, CLV, churn, survival, uplift, and causal analysis."

        system_prompt = (
            "You are an internal assistant for a bank or fintech analytics platform. "
            "Reply naturally and concisely. "
            "For greetings, greet the user and briefly mention you can help with business data, CLV, churn, survival, uplift, and causal analysis. "
            "Do not invent data when no tool has been called."
        )

        response = self._client.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=question)]
        )
        return response.content.strip()

    def generate_final_answer(
        self,
        question: str,
        route: str,
        tool_used: str,
        data: Any,
        charts_present: bool,
        sql: Optional[str] = None,
    ) -> str:
        if not self.available:
            return self._fallback_answer(question, route, tool_used, data)

        system_prompt = (
            "You are an internal analytics assistant for a bank or fintech company. "
            "Answer in a concise, business-friendly way. "
            "Ground the answer only in the provided tool output. "
            "Do not mention internal routing, tool names, SQL generation, or metadata unless the user explicitly asks. "
            "If charts are included, mention what they show without inventing values."
        )
        payload = {
            "question": question,
            "route": route,
            "tool_used": tool_used,
            "sql": sql,
            "charts_present": charts_present,
            "tool_output": data,
        }
        human_prompt = (
            "Create the final user-facing response for the frontend based on this JSON payload:\n"
            f"{json.dumps(payload, ensure_ascii=False, default=str)}"
        )

        response = self._client.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        return response.content.strip()

    @staticmethod
    def _fallback_answer(
        question: str,
        route: str,
        tool_used: str,
        data: Any,
    ) -> str:
        if route == "chat":
            return "Hello. I can help with business data, CLV, churn, survival, uplift, and causal analysis."

        if isinstance(data, dict):
            summary = json.dumps(data, ensure_ascii=False, default=str)
            return f"Here is the result for your request: {summary}"

        if isinstance(data, list):
            return f"I found {len(data)} result rows for your request."

        return f"I processed your request: {question}"
