from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    info = {
        "status": "ok",
        "supabase_url": bool(settings.SUPABASE_URL),
        "supabase_key_type": "sb_secret" if key.startswith("sb_") else "jwt/anon",
        "supabase_key_set": bool(settings.SUPABASE_KEY),
    }
    if settings.SUPABASE_URL and key:
        try:
            from app.core.database import get_supabase
            db = get_supabase()
            db.table("app_users").select("user_id", count="exact").limit(1).execute()
            info["database"] = "connected"
        except Exception as e:
            info["database"] = f"error: {type(e).__name__}: {e}"
    else:
        info["database"] = "missing config"
    return info
