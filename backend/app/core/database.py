"""Supabase / PostgREST client for the backend.

Uses ``postgrest.SyncPostgrestClient`` directly instead of the
``supabase`` package because the supabase-py client has compatibility
issues with newer API key formats on Render.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

from postgrest import SyncPostgrestClient

from app.core.config import settings


_SUPABASE_CREDENTIALS_HASH: str = ""


@lru_cache
def _build_client() -> SyncPostgrestClient:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    return SyncPostgrestClient(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers={"apikey": key},
    )


def get_supabase() -> SyncPostgrestClient:
    """Return a cached PostgREST client.

    To bypass Row Level Security, set ``SUPABASE_KEY`` to a Supabase
    ``service_role`` (or ``sb_secret_...``) key in the environment.
    Without it, the public ``anon`` key is used (respects RLS).
    """
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
