from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest import SyncPostgrestClient

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_raw_token(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials


def get_db(token: str = Depends(get_raw_token)) -> SyncPostgrestClient:
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    if not settings.SUPABASE_URL or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the backend .env file."
        )
    return SyncPostgrestClient(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {token}",
        },
    )
