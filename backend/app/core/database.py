from __future__ import annotations

import hashlib
from functools import lru_cache

from postgrest import SyncPostgrestClient

from app.core.config import settings


def _build_headers(key: str, user_token: str = "") -> dict[str, str]:
    headers = {}
    if key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
        headers["apikey"] = settings.SUPABASE_ANON_KEY
    else:
        headers["apikey"] = key
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
    return headers


_SUPABASE_CREDENTIALS_HASH: str = ""


@lru_cache
def _build_client(user_token: str = "") -> SyncPostgrestClient:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    return SyncPostgrestClient(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers=_build_headers(key, user_token=user_token),
    )


def get_supabase() -> SyncPostgrestClient:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    if not settings.SUPABASE_URL or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the backend .env file."
        )
    global _SUPABASE_CREDENTIALS_HASH
    combined = f"{settings.SUPABASE_URL}|{key}"
    current_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
    if _SUPABASE_CREDENTIALS_HASH and _SUPABASE_CREDENTIALS_HASH != current_hash:
        _build_client.cache_clear()
    _SUPABASE_CREDENTIALS_HASH = current_hash
    return _build_client()
