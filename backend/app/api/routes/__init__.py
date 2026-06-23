from fastapi import APIRouter

from app.api.routes import (
    chat,
    courses,
    finances,
    health,
    lessons,
    schools,
    scheduling,
    teachers,
    urgent,
    webhooks,
)

# Aggregate router. Register additional route modules here as the app grows.
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(schools.router)
api_router.include_router(teachers.router)
api_router.include_router(courses.router)
api_router.include_router(lessons.router)
api_router.include_router(scheduling.router)
api_router.include_router(webhooks.router)
api_router.include_router(chat.router)
api_router.include_router(urgent.router)
api_router.include_router(finances.router)
