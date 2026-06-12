from typing import Any, Dict, List


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
    return {
        "chart_id": "clv_top_k",
        "title": "Top Customers by CLV",
        "figure": {
            "data": [
                {
                    "type": "bar",
                    "x": [str(item["customer_id"]) for item in data],
                    "y": [float(item["clv"]) for item in data],
                    "marker": {"color": "#0f766e"},
                }
            ],
            "layout": {
                "title": {"text": "Top Customers by CLV"},
                "xaxis": {"title": {"text": "Customer"}},
                "yaxis": {"title": {"text": "CLV"}},
            },
        },
    }


def _build_survival_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "chart_id": "survival_top_k",
        "title": "Estimated Days Remaining to Churn",
        "figure": {
            "data": [
                {
                    "type": "bar",
                    "x": [str(item["customer_id"]) for item in data],
                    "y": [float(item["days_remaining_to_churn"]) for item in data],
                    "marker": {"color": "#b45309"},
                }
            ],
            "layout": {
                "title": {"text": "Estimated Days Remaining to Churn"},
                "xaxis": {"title": {"text": "Customer"}},
                "yaxis": {"title": {"text": "Days Remaining"}},
            },
        },
    }


def _build_churn_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "chart_id": "churn_top_k",
        "title": "Top Customers by Churn Probability",
        "figure": {
            "data": [
                {
                    "type": "bar",
                    "x": [str(item["customer_id"]) for item in data],
                    "y": [float(item["churn_probability"]) for item in data],
                    "marker": {"color": "#b91c1c"},
                }
            ],
            "layout": {
                "title": {"text": "Top Customers by Churn Probability"},
                "xaxis": {"title": {"text": "Customer"}},
                "yaxis": {"title": {"text": "Churn Probability"}},
            },
        },
    }


def _build_uplift_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    positive = int(data.get("num_customers_positive_uplift", 0))
    total = max(int(data.get("num_customers_scored", positive)), 1)
    non_positive = max(total - positive, 0)
    return {
        "chart_id": "uplift_distribution",
        "title": "Promotion Uplift Distribution",
        "figure": {
            "data": [
                {
                    "type": "pie",
                    "labels": ["Positive uplift", "Non-positive uplift"],
                    "values": [positive, non_positive],
                    "marker": {"colors": ["#15803d", "#9ca3af"]},
                    "hole": 0.45,
                }
            ],
            "layout": {"title": {"text": "Promotion Uplift Distribution"}},
        },
    }


def _build_causal_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    factors = data.get("churn_factors", [])
    if not factors:
        return {}

    return {
        "chart_id": "causal_factors",
        "title": "Potential Causal Drivers of Churn",
        "figure": {
            "data": [
                {
                    "type": "bar",
                    "x": [str(item["feature"]) for item in factors],
                    "y": [float(item["weight"]) for item in factors],
                    "marker": {"color": "#4338ca"},
                }
            ],
            "layout": {
                "title": {"text": "Potential Causal Drivers of Churn"},
                "xaxis": {"title": {"text": "Feature"}},
                "yaxis": {"title": {"text": "Weight"}},
            },
        },
    }
