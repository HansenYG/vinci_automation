import hashlib
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


_supabase_key_hash: str = ""


@lru_cache
def _build_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase() -> Client:
    """Return a cached Supabase client, rebuilding if the key has rotated.

    Use as a FastAPI dependency, e.g.:

        from fastapi import Depends
        from supabase import Client
        from app.core.database import get_supabase

        @router.get("/items")
        def list_items(db: Client = Depends(get_supabase)):
            return db.table("items").select("*").execute().data
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the backend .env file."
        )
    global _supabase_key_hash
    current_hash = hashlib.sha256(settings.SUPABASE_KEY.encode()).hexdigest()[:16]
    if _supabase_key_hash and _supabase_key_hash != current_hash:
        _build_client.cache_clear()
    _supabase_key_hash = current_hash
    return _build_client()
