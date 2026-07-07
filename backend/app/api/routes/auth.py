"""Authentication & authorization for Vinci Automation (Phase 1).

Users sign in on the frontend with Supabase Auth (Google OAuth or
email + password). The frontend sends the resulting Supabase access token
as a Bearer token on every API call. This module:

  * verifies the Supabase-issued JWT (HS256, signed with the project's
    JWT secret),
  * loads the caller's profile from public.app_users (role, teacher_id,
    is_vinci_email),
  * exposes FastAPI dependencies for server-side role checks
    (Business Rules v1.2 s.6A / s.12): 401 when unauthenticated,
    403 when the role is wrong,
  * exposes GET /api/auth/me so the frontend can resolve the session into
    a role and decide which UI to render (including the "Unauthorized,
    request registration" page when there is no app_users row).

No passwords, no custom users table: identity is owned by Supabase Auth and
roles are owned by public.app_users (populated by the on_auth_user_created
trigger per Business Rules s.18).
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.utils import base64url_decode  # noqa: F401  (ensures jose crypto is present)
from pydantic import BaseModel
from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase

# Bearer scheme; auto_error=False so we can return our own 401 shape.
bearer_scheme = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------- models
class AppUser(BaseModel):
    user_id: str
    email: str
    role: str                       # 'Admin' | 'Teacher'
    is_vinci_email: bool = False
    teacher_id: Optional[str] = None
    display_name: Optional[str] = None
    authorized: bool = True         # False => show "request registration"


# ------------------------------------------------------------------ jwt decode
# Supabase projects issue access tokens signed either with the legacy HS256
# shared secret OR with asymmetric JWT signing keys (ES256/RS256). We verify
# against the project's JWKS by default (works for asymmetric keys) and fall
# back to the HS256 shared secret when configured. The JWKS is cached.
_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _jwks_url(token: str = "") -> str:
    # Prefer the configured SUPABASE_URL.
    base = settings.SUPABASE_URL.rstrip("/")
    if base:
        return f"{base}/auth/v1/.well-known/jwks.json"
    # Fallback: derive from the JWT's issuer claim (so deployments that
    # don't set SUPABASE_URL can still validate tokens).
    if token:
        try:
            unverified = jwt.get_unverified_claims(token)
            iss = unverified.get("iss", "")
            if iss:
                return f"{iss.rstrip('/')}/.well-known/jwks.json"
        except JWTError:
            pass
    return ""


def _get_jwks(token: str = "", force: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    if (
        not force
        and _JWKS_CACHE["keys"] is not None
        and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS
    ):
        return _JWKS_CACHE["keys"]
    url = _jwks_url(token)
    if not url:
        return _JWKS_CACHE["keys"] or []
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["fetched_at"] = now
        return keys
    except Exception:
        return _JWKS_CACHE["keys"] or []


def _unverified_alg(token: str) -> str:
    try:
        return jwt.get_unverified_header(token).get("alg", "")
    except JWTError:
        return ""


def _decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Verify and decode a Supabase access token (asymmetric or HS256)."""
    alg = _unverified_alg(token)
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # HS256 (legacy shared secret) path.
    if alg == "HS256":
        if not settings.SUPABASE_JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server auth not configured for HS256 (missing SUPABASE_JWT_SECRET).",
            )
        try:
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        except JWTError as exc:
            raise cred_exc from exc

    # Asymmetric (ES256/RS256) path via JWKS.
    for attempt in range(2):
        keys = _get_jwks(token=token, force=(attempt == 1))
        if not keys:
            continue
        try:
            return jwt.decode(
                token,
                {"keys": keys},
                algorithms=["ES256", "RS256", "EdDSA"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        except JWTError:
            # Key may have rotated; retry once with a forced JWKS refresh.
            if attempt == 1:
                raise cred_exc
    raise cred_exc


def _is_vinci_email(email: str) -> bool:
    domain = (email or "").split("@")[-1].lower()
    return domain == settings.VINCI_EMAIL_DOMAIN.lower()


# ----------------------------------------------------------------- dependencies
async def get_token_payload(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, Any]:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_supabase_jwt(creds.credentials)


async def get_current_user(
    payload: dict[str, Any] = Depends(get_token_payload),
    db: Client = Depends(get_supabase),
) -> AppUser:
    """Resolve the authenticated identity into an app_users profile.

    If the token is valid but there is no app_users row, the account is
    unauthenticated for app purposes (Business Rules s.18 "Unauthorized,
    request registration"): we raise 403 so protected routes are blocked.
    The /me endpoint handles this case explicitly without raising.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    row = (
        db.table("app_users")
        .select("user_id, email, role, is_vinci_email, teacher_id, display_name")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: this account is not registered. Please request registration.",
        )

    u = row[0]
    return AppUser(
        user_id=u["user_id"],
        email=u["email"],
        role=u["role"],
        is_vinci_email=bool(u.get("is_vinci_email")),
        teacher_id=u.get("teacher_id"),
        display_name=u.get("display_name"),
        authorized=True,
    )


def require_role(*roles: str):
    """Dependency factory: allow only the given app_users roles."""
    async def _checker(current_user: AppUser = Depends(get_current_user)) -> AppUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role.",
            )
        return current_user
    return _checker


# Convenience deps used across the API.
require_admin = require_role("Admin")
require_authenticated = get_current_user


# ---------------------------------------------------------------------- routes
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
async def get_me(
    payload: dict[str, Any] = Depends(get_token_payload),
    db: Client = Depends(get_supabase),
):
    """Return the caller's profile and role.

    A valid Supabase session with no app_users row resolves to an
    "unauthorized" profile (authorized=False) so the frontend can render the
    "Unauthorized, request registration" page instead of erroring.
    """
    user_id = payload.get("sub")
    email = payload.get("email", "")

    row = (
        db.table("app_users")
        .select("user_id, email, role, is_vinci_email, teacher_id, display_name")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )

    if not row:
        # Valid login but not provisioned -> unauthorized (request registration).
        return AppUser(
            user_id=user_id or "",
            email=email,
            role="Teacher",
            is_vinci_email=_is_vinci_email(email),
            teacher_id=None,
            display_name=(email.split("@")[0] if email else None),
            authorized=False,
        )

    u = row[0]
    return AppUser(
        user_id=u["user_id"],
        email=u["email"],
        role=u["role"],
        is_vinci_email=bool(u.get("is_vinci_email")),
        teacher_id=u.get("teacher_id"),
        display_name=u.get("display_name"),
        authorized=True,
    )


@router.get("/health", include_in_schema=False)
async def auth_health():
    return {"auth": "supabase", "configured": bool(settings.SUPABASE_JWT_SECRET)}
