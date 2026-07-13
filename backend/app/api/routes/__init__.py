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

# SECURITY NOTE on service_role key usage:
# - Routes using Depends(get_db) pass the user's JWT token to PostgREST,
#   leveraging Row-Level Security (RLS) for authz.
# - Routes using Depends(get_supabase) use the service_role key which
#   bypasses RLS. Currently only used in:
#     1. webhooks.py — WATI webhook (no user session)
#     2. scheduling.py:run_due_reminders — cron job (no user session)
#     3. auth.py — user profile lookup (needed before user is resolved)
# - When adding new routes, prefer get_db over get_supabase unless
#   there is a documented reason why service_role access is required.
