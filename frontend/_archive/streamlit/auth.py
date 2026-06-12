import os
from typing import Any, Optional

import streamlit as st
from supabase import create_client


def auth_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required for login.")
    return create_client(url, key)


def init_auth_state() -> None:
    st.session_state.setdefault("auth_session", None)
    st.session_state.setdefault("auth_user_email", None)
    st.session_state.setdefault("auth_error", None)

    code = _query_param("code")
    if code and st.session_state.auth_session is None:
        try:
            response = get_supabase_client().auth.exchange_code_for_session({"auth_code": code})
            session = getattr(response, "session", None)
            user = getattr(response, "user", None)
            st.session_state.auth_session = session
            st.session_state.auth_user_email = getattr(user, "email", None)
            st.query_params.clear()
            st.rerun()
        except Exception as exc:
            st.session_state.auth_error = str(exc)


def access_token() -> Optional[str]:
    session = st.session_state.get("auth_session")
    if session is None:
        return None
    return getattr(session, "access_token", None)


def render_auth_gate() -> bool:
    init_auth_state()

    if access_token():
        with st.sidebar:
            st.caption(f"Signed in as {st.session_state.get('auth_user_email') or 'Google user'}")
            if st.button("Sign out", use_container_width=True):
                try:
                    get_supabase_client().auth.sign_out()
                except Exception:
                    pass
                st.session_state.auth_session = None
                st.session_state.auth_user_email = None
                st.rerun()
        return True

    st.title("FinChat Analytics")
    st.caption("Sign in with Google to access the customer analytics workspace.")

    if not auth_configured():
        st.error("Supabase Auth is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env.")
        return False

    if st.session_state.get("auth_error"):
        st.error(f"Sign-in failed: {st.session_state.auth_error}")

    login_url = _build_google_oauth_url()
    st.link_button("Sign in with Google", login_url, use_container_width=False)
    st.info("After Google sign-in, every authenticated user is scoped to tenant BANK001 for this MVP.")
    return False


def _build_google_oauth_url() -> str:
    redirect_to = os.getenv("STREAMLIT_BASE_URL", "http://localhost:8501")
    response = get_supabase_client().auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {
                "redirect_to": redirect_to,
            },
        }
    )
    return _extract_url(response)


def _extract_url(response: Any) -> str:
    url = getattr(response, "url", None)
    if url:
        return str(url)
    if isinstance(response, dict):
        data = response.get("data") or response
        if isinstance(data, dict) and data.get("url"):
            return str(data["url"])
    raise RuntimeError("Supabase did not return an OAuth URL.")


def _query_param(name: str) -> Optional[str]:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value
