import hashlib
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


_supabase_credentials_hash: str = ""


@lru_cache
def _build_client() -> Client:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    return create_client(settings.SUPABASE_URL, key)


def get_supabase() -> Client:
    """Return a cached Supabase client, rebuilding if credentials have changed.

    Use as a FastAPI dependency, e.g.:

        from fastapi import Depends
        from supabase import Client
        from app.core.database import get_supabase

        @router.get("/items")
        def list_items(db: Client = Depends(get_supabase)):
            return db.table("items").select("*").execute().data
    """
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    if not settings.SUPABASE_URL or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the backend .env file."
        )
    global _supabase_credentials_hash
    # Include both URL and KEY in the fingerprint to detect any credential/endpoint change
    combined = f"{settings.SUPABASE_URL}|{key}"
    current_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
    if _supabase_credentials_hash and _supabase_credentials_hash != current_hash:
        _build_client.cache_clear()
    _supabase_credentials_hash = current_hash
    return _build_client()
