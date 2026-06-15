from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Vinci Automation API"
    API_PREFIX: str = "/api"

    # Comma-separated list of origins allowed to call the API (CORS).
    CORS_ORIGINS: str = "http://localhost:5173"

    # Supabase credentials (set in .env).
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
