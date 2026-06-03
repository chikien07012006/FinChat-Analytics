from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    data: Any


class MLToolService:
    def __init__(self) -> None:
        self._tool_map: Dict[str, str] = {
            "calculate_clv_top_k": "calculate_clv_top_k",
            "survival_analysis_top_k": "survival_analysis_top_k",
            "churn_classification_top_k": "churn_classification_top_k",
            "uplift_modeling_positive": "uplift_modeling_positive",
            "discover_churn_factors": "discover_churn_factors",
        }

    def run(self, tool_name: str, k: int = 5) -> ToolResult:
        tool = self._load_tool(tool_name)
        if tool_name in {"uplift_modeling_positive", "discover_churn_factors"}:
            return ToolResult(tool_name=tool_name, data=tool())
        return ToolResult(tool_name=tool_name, data=tool(k=k))

    def _load_tool(self, tool_name: str) -> Callable[..., Any]:
        try:
            module = import_module("pipeline.train_all_models")
            return getattr(module, self._tool_map[tool_name])
        except Exception as exc:  # pragma: no cover - depends on runtime packages
            raise RuntimeError(
                f"Unable to load ML tool `{tool_name}`. Make sure pipeline dependencies are installed."
            ) from exc
