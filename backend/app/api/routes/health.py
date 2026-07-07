from fastapi import APIRouter
from jose import jwt

from app.core.config import settings

router = APIRouter()


def _key_role(key: str) -> str:
    if not key:
        return "none"
    if key.startswith("sb_"):
        return "sb_secret"
    try:
        claims = jwt.get_unverified_claims(key)
        return claims.get("role", "unknown")
    except Exception:
        return "unparseable"


@router.get("/health")
def health_check() -> dict:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    info = {
        "status": "ok",
        "supabase_url": settings.SUPABASE_URL or "(not set)",
        "supabase_key_role": _key_role(settings.SUPABASE_KEY),
        "effective_key_role": _key_role(key),
        "supabase_key_set": bool(settings.SUPABASE_KEY),
    }
    if settings.SUPABASE_URL and key:
        try:
            from app.core.database import get_supabase
            db = get_supabase()
            r = db.table("app_users").select("user_id", count="exact").limit(1).execute()
            info["database"] = f"connected (count={r.count})"
        except Exception as e:
            info["database"] = f"error: {type(e).__name__}: {e}"
    else:
        info["database"] = "missing config"
    return info
