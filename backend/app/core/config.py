from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Vinci Automation API"
    API_PREFIX: str = "/api"

    # Comma-separated list of origins allowed to call the API (CORS).
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Supabase Auth (Phase 1) ------------------------------------------
    # The frontend authenticates users with Supabase Auth (Google OAuth or
    # email + password). The backend validates the resulting access token.
    # SUPABASE_JWT_SECRET is the project's legacy JWT secret (Project
    # Settings -> API -> JWT Keys -> legacy). Used to verify HS256 tokens.
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    # Default to ES256 — Supabase projects created after 2024 use ES256 JWKS.
    # Set SUPABASE_JWT_ALGORITHM=HS256 only for legacy projects with a JWT secret.
    SUPABASE_JWT_ALGORITHM: str = os.getenv("SUPABASE_JWT_ALGORITHM", "ES256")
    # Vinci email domain that maps to the Admin role (Business Rules s.3).
    VINCI_EMAIL_DOMAIN: str = os.getenv("VINCI_EMAIL_DOMAIN", "vinciai.academy")

    # --- Supabase (set in .env) -------------------------------------------
    # Backend uses the service_role key, which bypasses RLS. Keep it secret.
    # SUPABASE_URL must be set in .env (no default — fail fast if missing).
    SUPABASE_URL: str = "https://zigzgzurmuplgcqsnnlv.supabase.co"
    SUPABASE_KEY: str = ""
    # Public anon key used by Supabase Auth API calls (safe to embed).
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppZ3pnenVybXVwbGdjcXNubmx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3NzUyMjIsImV4cCI6MjA5ODM1MTIyMn0.cGkHBdME80jDYDGRV_IBcGVp0k7IyCzxWSZOLqsZcIQ"

    # --- WATI (WhatsApp) --------------------------------------------------
    # ENDPOINT_BASE includes the tenant id, e.g. https://live-mt-server.wati.io/111307
    WATI_API_URL: str = ""
    WATI_ACCESS_TOKEN: str = ""          # raw JWT; "Bearer " is added in code
    WATI_TEMPLATE_UNASSIGNED: str = "unassigned_lesson_notification"
    WATI_TEMPLATE_CONFIRMATION: str = "tutor_confirmation_extra_info"
    WATI_TEMPLATE_CANCEL_ADMIN: str = "tutor_cancellation_or_reschedule_admin_reminder"
    WATI_BROADCAST_PREFIX: str = "vinci"
    # Shared secret sent as Authorization: Bearer <secret> header to reject spoofed calls.
    WATI_WEBHOOK_SECRET: str = ""

    # Admin + fallback WhatsApp numbers (digits only, no leading +).
    ADMIN_WHATSAPP: str = ""
    FALLBACK_WHATSAPP_HK: str = "85252408480"
    FALLBACK_WHATSAPP_ID: str = "6281287776026"

    # --- Business rules (ported from the Apps Scripts) --------------------
    URGENT_WINDOW_DAYS: int = 7          # within this many days => "urgent" / red
    REBLAST_INTERVAL_HOURS: int = 24     # re-blast the pool at most once per day

    # --- Airtable (optional one-time migration of legacy tutor data) ------
    AIRTABLE_API_KEY: str = ""
    AIRTABLE_BASE_ID: str = ""
    AIRTABLE_TEACHERS_TABLE: str = "Teachers"
    AIRTABLE_LESSONS_TABLE: str = "Lessons"

    # --- LLM for the chatbot ---------------------------------------------
    # provider = "openai" (OpenAI-compatible, default) or "ollama" (local dev)
    # For production, set LLM_PROVIDER=openai, LLM_API_KEY=<openrouter key>,
    # LLM_BASE_URL=https://openrouter.ai/api/v1, LLM_MODEL=meta-llama/llama-3.1-8b-instruct
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""                # required for openai-compatible providers
    LLM_BASE_URL: str = ""               # default depends on provider (see below)
    LLM_MODEL: str = ""                  # default depends on provider (see below)
    LLM_TIMEOUT_SECONDS: int = 60

    @property
    def llm_base_url(self) -> str:
        if self.LLM_BASE_URL:
            return self.LLM_BASE_URL
        return {
            "ollama": "http://localhost:11434",
            "openai": "https://openrouter.ai/api/v1",
        }.get(self.LLM_PROVIDER, "https://openrouter.ai/api/v1")

    @property
    def llm_model(self) -> str:
        if self.LLM_MODEL:
            return self.LLM_MODEL
        return {
            "ollama": "llama3.1",
            "openai": "meta-llama/llama-3.1-8b-instruct",
        }.get(self.LLM_PROVIDER, "meta-llama/llama-3.1-8b-instruct")

    # --- In-process scheduler (reminders / re-blast) ----------------------
    # Off by default. On Render, prefer a Cron Job hitting the trigger
    # endpoints; flip this on for a single always-on worker instead.
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_TICK_MINUTES: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
