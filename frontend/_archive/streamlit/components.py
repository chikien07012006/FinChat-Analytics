import streamlit as st
import httpx
import pandas as pd
import json

def load_custom_css():
    st.markdown("""
        <style>
        /* Custom UI Tweaks for a more premium feel */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .kpi-card {
            background-color: #1e1e2f;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }
        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            color: #00d4ff;
        }
        .kpi-label {
            font-size: 0.9rem;
            color: #a0a0b0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
        }
        </style>
    """, unsafe_allow_html=True)


def _auth_headers(access_token: str | None):
    return {"Authorization": f"Bearer {access_token}"} if access_token else {}


def fetch_kpis(backend_url: str, access_token: str | None):
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(f"{backend_url.rstrip('/')}/api/kpis", headers=_auth_headers(access_token))
            res.raise_for_status()
            return res.json()
    except Exception:
        return None


def render_kpi_dashboard(backend_url: str, access_token: str | None):
    st.markdown("### Executive Dashboard")
    kpis = fetch_kpis(backend_url, access_token)
    
    if kpis:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{(kpis["churn_rate"]*100):.1f}%</div><div class="kpi-label">Avg Churn Rate</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">${kpis["avg_clv"]:,.0f}</div><div class="kpi-label">Avg CLV</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{kpis["total_customers"]:,}</div><div class="kpi-label">Total Customers</div></div>', unsafe_allow_html=True)
            
        st.markdown("#### Segment Distribution")
        df_segments = pd.DataFrame(list(kpis["segment_distribution"].items()), columns=["Segment", "Count"])
        st.bar_chart(df_segments.set_index("Segment"))
    else:
        st.warning("Could not load KPIs from backend.")


def render_upload_section(backend_url: str, access_token: str | None):
    st.markdown("### Upload Transaction Data")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file is not None:
        if st.button("Process Data", use_container_width=True):
            with st.spinner("Uploading and processing data..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    with httpx.Client(timeout=60.0) as client:
                        res = client.post(
                            f"{backend_url.rstrip('/')}/api/upload",
                            files=files,
                            headers=_auth_headers(access_token),
                        )
                        res.raise_for_status()
                        result = res.json()
                        st.success(f"Processed {result.get('rows_processed', 0)} rows successfully!")
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")


def export_report_button(messages: list):
    st.markdown("### Export")
    if not messages:
        st.button("Export Report (PDF)", disabled=True, use_container_width=True)
        return
        
    report_content = "FinChat Analytics Report\n\n"
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        report_content += f"{role}: {m['content']}\n\n"
        
    st.download_button(
        label="Export Chat History",
        data=report_content,
        file_name="finchat_report.txt",
        mime="text/plain",
        use_container_width=True
    )
