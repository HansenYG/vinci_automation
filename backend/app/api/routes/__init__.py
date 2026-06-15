from fastapi import APIRouter

from app.api.routes import health

# Aggregate router. Register additional route modules here as the app grows.
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
