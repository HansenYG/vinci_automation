from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings


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


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Add API health check endpoint
    @app.get("/api/health", include_in_schema=False)
    async def health_check():
        from datetime import datetime
        from supabase import Client
        from app.core.database import get_supabase
        
        db: Client = get_supabase()
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
