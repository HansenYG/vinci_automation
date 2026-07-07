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


JWKS_ALGORITHMS = ["ES256", "RS256", "EdDSA"]


def _supabase_base(user_token: str = "") -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    if base:
        return base
    # Fallback: try each known key JWT for the project URL.
    # The token's issuer claim looks like
    # "https://<project>.supabase.co/auth/v1"; the API keys have
    # iss="supabase" (not a URL) so we ignore those.
    for candidate in [settings.SUPABASE_KEY, settings.SUPABASE_ANON_KEY, user_token]:
        if not candidate:
            continue
        try:
            unverified = jwt.get_unverified_claims(candidate)
            iss = unverified.get("iss", "")
            if iss and iss.startswith("http"):
                return iss.rstrip("/auth/v1").rstrip("/")
        except (JWTError, Exception):
            pass
    return ""


def _get_jwks(force: bool = False, user_token: str = "") -> list[dict[str, Any]]:
    now = time.time()
    if (
        not force
        and _JWKS_CACHE["keys"] is not None
        and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS
    ):
        return _JWKS_CACHE["keys"]
    base = _supabase_base(user_token=user_token)
    if not base:
        return []
    try:
        resp = httpx.get(f"{base}/auth/v1/.well-known/jwks.json", timeout=10)
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


def _verify_via_supabase(token: str) -> dict[str, Any] | None:
    """Verify a user access token by calling the Supabase Auth /user endpoint.

    This fallback works even when local JWKS resolution fails (e.g. Render
    free-tier cannot make outbound HTTPS calls to the JWKS endpoint).
    """
    base = _supabase_base(user_token=token)
    if not base:
        return None
    # The apikey header is required by Supabase REST; use whichever key is
    # available (service_role or public anon key). The anon key is safe
    # to expose (it ships in the frontend JS bundle).
    api_key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    if not api_key:
        return None
    try:
        resp = httpx.get(
            f"{base}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except httpx.HTTPError:
        pass
    return None


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

    # Asymmetric (ES256/RS256) — try local JWKS decode first, then fall back
    # to Supabase Auth's own /user endpoint for environments where the backend
    # cannot reach the JWKS URL (e.g. Render free-tier network isolation).
    for attempt in range(2):
        keys = _get_jwks(force=(attempt == 1), user_token=token)
        if keys:
            try:
                return jwt.decode(
                    token,
                    {"keys": keys},
                    algorithms=JWKS_ALGORITHMS,
                    audience="authenticated",
                    options={"verify_aud": True},
                )
            except JWTError:
                if attempt == 1:
                    break

    user_data = _verify_via_supabase(token)
    if user_data:
        sub = user_data.get("id", "")
        email = user_data.get("email", "")
        if sub:
            return {"sub": sub, "email": email, "role": "authenticated"}

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
):
    """Return the caller's profile and role.

    A valid Supabase session with no app_users row resolves to an
    "unauthorized" profile (authorized=False) so the frontend can render the
    "Unauthorized, request registration" page instead of erroring.
    """
    user_id = payload.get("sub")
    email = payload.get("email", "")

    def _unauthorized() -> AppUser:
        return AppUser(
            user_id=user_id or "",
            email=email,
            role="Teacher",
            is_vinci_email=_is_vinci_email(email),
            teacher_id=None,
            display_name=(email.split("@")[0] if email else None),
            authorized=False,
        )

    try:
        db = get_supabase()
    except RuntimeError:
        return _unauthorized()

    try:
        row = (
            db.table("app_users")
            .select("user_id, email, role, is_vinci_email, teacher_id, display_name")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
    except Exception:
        return _unauthorized()

    if not row:
        return _unauthorized()

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
