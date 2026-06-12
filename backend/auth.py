from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    email: Optional[str]
    tenant_id: str
    claims: Dict[str, Any]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Supabase bearer token.",
        )

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth is not configured.",
        )

    user = _fetch_supabase_user(
        supabase_url=settings.supabase_url,
        anon_key=settings.supabase_anon_key,
        access_token=credentials.credentials,
    )

    user_id = str(user.get("id") or user.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase user token.",
        )

    return AuthContext(
        user_id=user_id,
        email=user.get("email"),
        tenant_id=settings.tenant_id,
        claims=user,
    )


def _fetch_supabase_user(supabase_url: str, anon_key: str, access_token: str) -> Dict[str, Any]:
    url = f"{supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to validate Supabase user token.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase user token.",
        )

    data = response.json()
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase user response.",
        )
    return data
