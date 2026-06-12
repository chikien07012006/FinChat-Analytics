from typing import Any, Dict, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import plotly.graph_objects as go
import streamlit as st

from frontend.components import load_custom_css, render_kpi_dashboard, render_upload_section, export_report_button


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_TENANT_ID = "BANK001"
SUGGESTED_PROMPTS = [
    "Show me the top 5 customers with the highest CLV for upselling",
    "Which customers have the highest churn probability?",
    "What is the top 10 customers by total transaction amount?",
    "How many customers have positive uplift?",
    "What are the main causal drivers of churn?",
]


st.set_page_config(
    page_title="FinChat Analytics Tester",
    page_icon="FA",
    layout="wide",
)


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("backend_url", DEFAULT_BACKEND_URL)
    st.session_state.setdefault("tenant_id", DEFAULT_TENANT_ID)


def call_backend(backend_url: str, message: str, tenant_id: str) -> Dict[str, Any]:
    payload = {"message": message, "tenant_id": tenant_id or None}

    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{backend_url.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()


def render_plotly_charts(charts: List[Dict[str, Any]]) -> None:
    if not charts:
        return

    st.markdown("#### Visualizations")
    for chart in charts:
        figure_json = chart.get("figure", {})
        try:
            fig = go.Figure(figure_json)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.warning(f"Unable to render one of the charts returned by the backend. {exc}")


def render_message(message: Dict[str, Any]) -> None:
    role = message["role"]
    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(message["content"])

        if role == "assistant":
            response = message.get("response_payload", {})
            charts = response.get("charts", [])
            render_plotly_charts(charts)


def submit_message(message: str) -> None:
    st.session_state.messages.append({"role": "user", "content": message})

    try:
        result = call_backend(
            backend_url=st.session_state.backend_url,
            message=message,
            tenant_id=st.session_state.tenant_id,
        )
        answer = result.get("answer", "No answer returned.")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "response_payload": result,
            }
        )
    except httpx.HTTPStatusError as exc:
        detail = None
        try:
            detail = exc.response.json().get("detail")
        except Exception:
            detail = None

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    f"Backend returned an error: {exc.response.status_code}. {detail}"
                    if detail
                    else f"Backend returned an error: {exc.response.status_code}."
                ),
                "response_payload": {"charts": []},
            }
        )
    except Exception as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Unable to reach the backend. {exc}",
                "response_payload": {"charts": []},
            }
        )


def sidebar() -> None:
    with st.sidebar:
        st.markdown("## FinChat Analytics")
        st.caption("AI-Powered Customer Retention Platform")
        st.divider()

        render_kpi_dashboard(st.session_state.backend_url)
        st.divider()

        render_upload_section(st.session_state.backend_url)
        st.divider()

        export_report_button(st.session_state.messages)
        st.divider()

        with st.expander("Settings & Tools"):
            st.session_state.backend_url = st.text_input(
                "Backend URL",
                value=st.session_state.backend_url,
                help="Example: http://127.0.0.1:8000",
            )
            st.session_state.tenant_id = st.text_input(
                "Tenant ID",
                value=st.session_state.tenant_id,
            )

            if st.button("Check /health", use_container_width=True):
                try:
                    with httpx.Client(timeout=20.0) as client:
                        response = client.get(f"{st.session_state.backend_url.rstrip('/')}/health")
                        response.raise_for_status()
                        st.success("Backend is reachable.")
                except Exception as exc:
                    st.error(f"Health check failed: {exc}")

            if st.button("Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

            st.markdown("### Prompt ideas")
            for idx, prompt in enumerate(SUGGESTED_PROMPTS):
                if st.button(prompt, key=f"prompt_{idx}", use_container_width=True):
                    submit_message(prompt)
                    st.rerun()


def main() -> None:
    load_custom_css()
    init_state()
    sidebar()

    st.title("Data Insights Agent")
    st.caption("Ask questions about churn, CLV, and campaign uplift.")

    if not st.session_state.messages:
        st.info("👋 Welcome! Use the sidebar to upload your latest transactions, or start asking questions below.")

    for message in st.session_state.messages:
        render_message(message)

    if prompt := st.chat_input("Ask a business or ML analytics question..."):
        submit_message(prompt)
        st.rerun()


if __name__ == "__main__":
    main()
