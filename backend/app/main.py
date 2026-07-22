import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import api_router
from app.core.config import settings

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optionally run the reminder/re-blast sweep in-process. Off by default;
    # on Render prefer a Cron Job hitting /api/scheduling/run-due-reminders.
    scheduler = None
    if settings.ENABLE_SCHEDULER:
        from app.services.scheduler import start_scheduler

        scheduler = start_scheduler()

    # Auth identities are owned by Supabase Auth + the on_auth_user_created
    # trigger (Business Rules s.18); no app-side admin bootstrap is needed.

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def create_app() -> FastAPI:
    log.info("Starting Vinci Automation API — creating FastAPI app")
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=0,
    )

    # Security headers middleware — mitigates XSS, clickjacking, MIME sniffing
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Add API health check endpoint
    @app.get("/api/health", include_in_schema=False)
    async def health_check():
        from datetime import datetime
        from postgrest import SyncPostgrestClient
        from app.core.database import get_supabase
        
        db: SyncPostgrestClient = get_supabase()
        health_status = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {}
        }
        
        # Check database connection (count is a HEAD query; empty tables are fine)
        try:
            db.table("app_users").select("user_id", count="exact").limit(1).execute()
            health_status["services"]["database"] = "connected"
        except Exception as e:
            health_status["services"]["database"] = f"error: {str(e)}"
        
        # Check WATI configuration
        health_status["services"]["wati"] = "configured" if settings.WATI_API_URL and settings.WATI_ACCESS_TOKEN else "not configured"
        
        # Check LLM configuration
        health_status["services"]["llm"] = "configured" if settings.LLM_PROVIDER else "not configured"
        
        return health_status

    return app


app = create_app()
