from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Vinci Automation API"
    API_PREFIX: str = "/api"

    # Comma-separated list of origins allowed to call the API (CORS).
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Supabase (set in .env) -------------------------------------------
    # Backend uses the service_role key, which bypasses RLS. Keep it secret.
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # --- WATI (WhatsApp) --------------------------------------------------
    # ENDPOINT_BASE includes the tenant id, e.g. https://live-mt-server.wati.io/111307
    WATI_API_URL: str = ""
    WATI_ACCESS_TOKEN: str = ""          # raw JWT; "Bearer " is added in code
    WATI_TEMPLATE_UNASSIGNED: str = "unassigned_lesson_notification"
    WATI_TEMPLATE_CONFIRMATION: str = "tutor_confirmation_extra_info"
    WATI_TEMPLATE_CANCEL_ADMIN: str = "tutor_cancellation_or_reschedule_admin_reminder"
    WATI_BROADCAST_PREFIX: str = "vinci"
    # Shared secret appended to the webhook URL (?token=...) to reject spoofed calls.
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

    # --- Ollama (free local LLM for the chatbot) --------------------------
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_TIMEOUT_SECONDS: int = 60

    # --- In-process scheduler (reminders / re-blast) ----------------------
    # Off by default. On Render, prefer a Cron Job hitting the trigger
    # endpoints; flip this on for a single always-on worker instead.
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_TICK_MINUTES: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
