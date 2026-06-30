from fastapi import APIRouter, Depends

from app.api.routes import (
    auth,
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
from app.api.routes.auth import require_admin, require_authenticated

# Aggregate router. Register additional route modules here as the app grows.
api_router = APIRouter()

# Public routes (no auth): health checks and the auth endpoints themselves.
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])

# The WATI inbound webhook is machine-to-machine and authenticated by its own
# signature/verify-token check inside the route, so it is intentionally not
# behind the user-session guard.
api_router.include_router(webhooks.router)

# Authenticated routes — every request must carry a valid Supabase session that
# resolves to a registered app_users row (Business Rules v1.2 s.6A).
_auth = [Depends(require_authenticated)]
api_router.include_router(schools.router, dependencies=_auth)
api_router.include_router(teachers.router, dependencies=_auth)
api_router.include_router(courses.router, dependencies=_auth)
api_router.include_router(lessons.router, dependencies=_auth)
api_router.include_router(scheduling.router, dependencies=_auth)
api_router.include_router(chat.router, dependencies=_auth)
api_router.include_router(urgent.router, dependencies=_auth)

# Finances is Admin-only (Business Rules v1.2 s.12).
api_router.include_router(finances.router, dependencies=[Depends(require_admin)])
