from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
import secrets
from supabase import Client
from app.core.database import get_supabase
from app.core.config import settings

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated=["auto"])

# JWT token settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", settings.JWT_SECRET_KEY)
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# OAuth2 scheme for FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", schemeName="JWT")

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "admin"

class UserLogin(BaseModel):
    username: str
    password: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get current user from JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    db: Client = get_supabase()
    user = db.table("users").select("*").eq("username", token_data.username).execute().data
    if not user:
        raise credentials_exception
    
    return user[0]

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based access control
def require_role(role: str):
    async def role_checker(current_user: dict = Depends(get_current_active_user)):
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return current_user
    return role_checker

# Auth API endpoints router
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Client = Depends(get_supabase)):
    existing_user = db.table("users").select("*").eq("username", user.username).execute().data
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "role": user.role,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = db.table("users").insert(user_data).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    return {"message": "User created successfully", "user_id": result.data[0]["id"]}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Client = Depends(get_supabase)):
    user = db.table("users").select("*").eq("username", form_data.username).execute().data
    if not user or not verify_password(form_data.password, user[0]["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user[0].get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[0]["username"], "role": user[0]["role"], "user_id": user[0]["id"]}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_active_user)):
    return {
        "id": current_user.get("id"),
        "username": current_user.get("username"),
        "email": current_user.get("email"),
        "role": current_user.get("role")
    }

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}

# User management endpoints (admin only)
@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_role("admin"))
):
    db: Client = get_supabase()
    users = db.table("users").select("*").range(skip, skip + limit - 1).execute().data
    return users

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: dict,
    current_user: dict = Depends(require_role("admin"))
):
    if "username" in updates or "email" in updates or "hashed_password" in updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update username, email, or password directly. Use dedicated endpoints."
        )
    
    db: Client = get_supabase()
    result = db.table("users").update(updates).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User updated successfully"}

# Password change endpoint
@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_active_user)
):
    db: Client = get_supabase()
    user = db.table("users").select("*").eq("id", current_user["id"]).execute().data
    
    if not verify_password(current_password, user[0]["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    hashed_password = get_password_hash(new_password)
    db.table("users").update({"hashed_password": hashed_password}).eq("id", current_user["id"]).execute()
    
    return {"message": "Password changed successfully"}

# Admin endpoints for system management
@router.get("/system/stats")
async def system_stats(current_user: dict = Depends(require_role("admin"))):
    db: Client = get_supabase()
    stats = {}
    
    for table in ["lessons", "teachers", "courses", "schools", "urgent_news", "lesson_events"]:
        result = db.table(table).select("*").execute()
        stats[table] = len(result.data) if result.data else 0
    
    return stats

@router.get("/system/health")
async def system_health(current_user: dict = Depends(require_role("admin"))):
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }