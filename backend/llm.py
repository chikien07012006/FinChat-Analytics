import json
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import get_settings


class GeminiService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

        if self.settings.llm_configured:
            self._client = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,
                api_key=self.settings.gemini_api_key,
                temperature=0.2,
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
                else:
                    text_value = getattr(item, "text", None)
                    if isinstance(text_value, str):
                        text_parts.append(text_value)

            combined = "\n".join(part.strip() for part in text_parts if part and part.strip())
            if combined:
                return combined

        if isinstance(content, dict):
            text_value = content.get("text")
            if isinstance(text_value, str):
                return text_value.strip()

        text_value = getattr(content, "text", None)
        if isinstance(text_value, str):
            return text_value.strip()

        return str(content).strip()

    @staticmethod
    def _format_number(value: Any) -> str:
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)

    def _summarize_sql_rows(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return "I did not find matching records for this request. You may want to broaden the filters or time range."

        sample = data[:3]
        columns = list(sample[0].keys())
        lead_column = columns[0] if columns else "record"
        metric_column = next(
            (
                col for col in columns
                if any(token in col.lower() for token in ["amount", "total", "revenue", "value", "count"])
            ),
            columns[1] if len(columns) > 1 else None,
        )

        lines = [f"I found {len(data)} records that match your request."]
        if metric_column:
            examples = ", ".join(
                f"{row.get(lead_column, 'N/A')} ({metric_column}: {self._format_number(row.get(metric_column, 'N/A'))})"
                for row in sample
            )
            lines.append(f"Top examples include {examples}.")

        lines.append("These results are useful for identifying high-value customers or segments for priority servicing, cross-sell, and retention actions.")
        return " ".join(lines)

    def _summarize_tool_output(self, route: str, tool_used: str, data: Any) -> str:
        if route == "chat":
            return "Hello. I can help with business data, CLV, churn, survival, uplift, and causal analysis."

        if tool_used == "uplift_modeling_positive" and isinstance(data, dict):
            positive = int(data.get("num_customers_positive_uplift", 0))
            total = max(int(data.get("num_customers_scored", 0)), 0)
            if total == 0:
                return (
                    "I could not score customers for uplift from the current dataset. "
                    "Please check that promotion and conversion data are available."
                )

            ratio = positive / total
            strategy = (
                "You can prioritize promotion campaigns for a broad eligible audience and then refine targeting with profitability or segment rules."
                if ratio >= 0.5
                else "You should keep promotions targeted instead of broad-based, focusing on segments with stronger expected response."
            )
            return (
                f"{self._format_number(positive)} out of {self._format_number(total)} customers show positive predicted uplift "
                f"({ratio:.1%}). {strategy}"
            )

        if tool_used == "discover_churn_factors" and isinstance(data, dict):
            factors = data.get("churn_factors", [])
            if not factors:
                return (
                    "I did not find strong causal churn drivers from the current feature set. "
                    "This usually means the available data does not separate clear direct drivers yet, so the next step is to enrich the dataset "
                    "with behavior, service usage, complaints, channel activity, or campaign history before drawing strategy conclusions."
                )

            top_factors = factors[:3]
            factor_text = ", ".join(
                f"{item.get('feature', 'unknown feature')} ({item.get('weight', 0)})"
                for item in top_factors
            )
            return (
                f"The strongest potential churn drivers in the current analysis are {factor_text}. "
                "These features should be reviewed first for retention strategy, customer monitoring, and early-warning rules."
            )

        if tool_used == "churn_classification_top_k" and isinstance(data, list):
            if not data:
                return "I could not identify high-risk customers from the current dataset."

            top = data[:3]
            examples = ", ".join(
                f"{item.get('customer_id', 'N/A')} ({float(item.get('churn_probability', 0)):.1%} churn risk)"
                for item in top
            )
            return (
                f"The highest-risk customers include {examples}. These customers should be prioritized for retention outreach, service recovery, "
                "or personalized offers before applying broad campaigns."
            )

        if tool_used == "calculate_clv_top_k" and isinstance(data, list):
            if not data:
                return "I could not identify high-CLV customers from the current dataset."

            top = data[:3]
            examples = ", ".join(
                f"{item.get('customer_id', 'N/A')} (CLV: {self._format_number(float(item.get('clv', 0)))})"
                for item in top
            )
            return (
                f"The highest-value customers include {examples}. These customers are good candidates for premium servicing, upsell, "
                "and loyalty strategies."
            )

        if tool_used == "survival_analysis_top_k" and isinstance(data, list):
            if not data:
                return "I could not estimate remaining time to churn from the current dataset."

            top = data[:3]
            examples = ", ".join(
                f"{item.get('customer_id', 'N/A')} ({self._format_number(float(item.get('days_remaining_to_churn', 0)))} days remaining)"
                for item in top
            )
            return (
                f"The most urgent retention cases include {examples}. These customers likely need immediate intervention, such as proactive contact, "
                "benefit reminders, or tailored retention offers."
            )

        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return self._summarize_sql_rows(data)

        if isinstance(data, dict):
            return f"I processed your request successfully. Key output: {json.dumps(data, ensure_ascii=False, default=str)}"

        return "I processed your request successfully."

    def generate_sql(self, question: str, schema_text: str, tenant_id: Optional[str] = None) -> str:
        if not self.available:
            raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to .env before using Text2SQL.")

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
        return self._extract_text(response.content)

    def classify_route(self, question: str) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to .env before routing with LLM.")

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
        content = self._extract_text(response.content)
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

        try:
            response = self._client.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=question)]
            )
            return self._extract_text(response.content)
        except Exception:
            return "Hello. I can help with business data, CLV, churn, survival, uplift, and causal analysis."

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
            "If charts are included, mention what they show without inventing values. "
            "When possible, briefly explain the business implication and the most sensible next action for the user."
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

        try:
            response = self._client.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            )
            return self._extract_text(response.content)
        except Exception:
            return self._fallback_answer(question, route, tool_used, data)

    def _fallback_answer(
        self,
        question: str,
        route: str,
        tool_used: str,
        data: Any,
    ) -> str:
        return self._summarize_tool_output(route=route, tool_used=tool_used, data=data)
