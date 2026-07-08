from fastapi import APIRouter
from jose import jwt

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    key = settings.SUPABASE_KEY
    info = {"status": "ok"}
    if key:
        try:
            claims = jwt.get_unverified_claims(key)
            info["key_role"] = claims.get("role")
            info["key_prefix"] = key[:20] + "..."
        except Exception:
            info["key_role"] = "unparseable"
    else:
        info["key_role"] = "not set"
    return info
