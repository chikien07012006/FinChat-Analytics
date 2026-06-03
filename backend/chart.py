from typing import Any, Dict, List

import plotly.graph_objects as go


def build_ml_chart(tool_name: str, data: Any) -> List[Dict[str, Any]]:
    builders = {
        "calculate_clv_top_k": _build_clv_chart,
        "survival_analysis_top_k": _build_survival_chart,
        "churn_classification_top_k": _build_churn_chart,
        "uplift_modeling_positive": _build_uplift_chart,
        "discover_churn_factors": _build_causal_chart,
    }
    builder = builders.get(tool_name)
    if builder is None:
        return []
    chart = builder(data)
    return [chart] if chart else []


def _build_clv_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    fig = go.Figure(
        data=[
            go.Bar(
                x=[item["customer_id"] for item in data],
                y=[item["clv"] for item in data],
                marker_color="#0f766e",
            )
        ]
    )
    fig.update_layout(title="Top Customers by CLV", xaxis_title="Customer", yaxis_title="CLV")
    return {"chart_id": "clv_top_k", "title": "Top Customers by CLV", "figure": fig.to_plotly_json()}


def _build_survival_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    fig = go.Figure(
        data=[
            go.Bar(
                x=[item["customer_id"] for item in data],
                y=[item["days_remaining_to_churn"] for item in data],
                marker_color="#b45309",
            )
        ]
    )
    fig.update_layout(
        title="Estimated Days Remaining to Churn",
        xaxis_title="Customer",
        yaxis_title="Days Remaining",
    )
    return {
        "chart_id": "survival_top_k",
        "title": "Estimated Days Remaining to Churn",
        "figure": fig.to_plotly_json(),
    }


def _build_churn_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    fig = go.Figure(
        data=[
            go.Bar(
                x=[item["customer_id"] for item in data],
                y=[item["churn_probability"] for item in data],
                marker_color="#b91c1c",
            )
        ]
    )
    fig.update_layout(
        title="Top Customers by Churn Probability",
        xaxis_title="Customer",
        yaxis_title="Churn Probability",
    )
    return {
        "chart_id": "churn_top_k",
        "title": "Top Customers by Churn Probability",
        "figure": fig.to_plotly_json(),
    }


def _build_uplift_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    positive = int(data.get("num_customers_positive_uplift", 0))
    total = max(int(data.get("num_customers_scored", positive)), 1)
    non_positive = max(total - positive, 0)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positive uplift", "Non-positive uplift"],
                values=[positive, non_positive],
                marker=dict(colors=["#15803d", "#9ca3af"]),
                hole=0.45,
            )
        ]
    )
    fig.update_layout(title="Promotion Uplift Distribution")
    return {
        "chart_id": "uplift_distribution",
        "title": "Promotion Uplift Distribution",
        "figure": fig.to_plotly_json(),
    }


def _build_causal_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    factors = data.get("churn_factors", [])
    fig = go.Figure(
        data=[
            go.Bar(
                x=[item["feature"] for item in factors],
                y=[item["weight"] for item in factors],
                marker_color="#4338ca",
            )
        ]
    )
    fig.update_layout(title="Potential Causal Drivers of Churn", xaxis_title="Feature", yaxis_title="Weight")
    return {
        "chart_id": "causal_factors",
        "title": "Potential Causal Drivers of Churn",
        "figure": fig.to_plotly_json(),
    }
