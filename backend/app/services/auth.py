"""Authentication service for user management and JWT token handling."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any

from jose import jwt
from passlib.context import CryptContext
from supabase import Client

from app.core.config import settings

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated=["auto"])
# JWT token settings
SECRET_KEY = settings.JWT_SECRET_KEY or ""
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a hash for the given password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode a JWT access token."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def create_initial_admin_user(db: Client) -> bool:
    """Create the initial admin user if it doesn't exist."""
    # Check if admin user already exists
    existing_users = db.table("users").select("*").eq("role", "admin").execute()
    if existing_users.data:
        return False

    # Create admin user
    hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
    admin_data = {
        "username": settings.ADMIN_USERNAME,
        "email": settings.ADMIN_EMAIL,
        "hashed_password": hashed_password,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    db.table("users").insert(admin_data).execute()
    return True


def verify_user_credentials(db: Client, username: str, password: str) -> Dict[str, Any] | None:
    """Verify user credentials against the database."""
    result = db.table("users").select("*").eq("username", username).execute()
    if not result.data:
        return None

    user = result.data[0]
    if not user.get("is_active", True):
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    # Remove sensitive data before returning
    user.pop("hashed_password", None)
    return user


def validate_token(token: str) -> Dict[str, Any] | None:
    """Validate a JWT token and return its payload if valid."""
    try:
        payload = decode_access_token(token)

        if not payload or "sub" not in payload:
            return None

        return payload
    except Exception:
        return None


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Longer expiry for refresh tokens
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def rotate_access_token(db: Client, refresh_token: str) -> Dict[str, str] | None:
    """Rotate access token using a refresh token."""
    try:
        payload = decode_access_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        username = payload.get("sub")
        if not username:
            return None

        user = verify_user_credentials(db, username, "")
        if not user:
            return None

        new_access_token = create_access_token({
            "sub": username,
            "role": user.get("role"),
            "user_id": user.get("id"),
        })

        return {"access_token": new_access_token}
    except Exception:
        return None


def update_user_last_login(db: Client, user_id: str) -> None:
    """Update the last login time for a user."""
    db.table("users").update({
        "last_login": datetime.utcnow().isoformat()
    }).eq("id", user_id).execute()


def is_token_valid(token: str, expected_username: str | None = None) -> bool:
    """Check if a token is valid and optionally check username match."""
    payload = validate_token(token)
    if not payload:
        return False

    if expected_username and payload.get("sub") != expected_username:
        return False

    return True
