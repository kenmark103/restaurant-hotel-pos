from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── Database & cache ──────────────────────────────────────────────────────
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Cryptography ──────────────────────────────────────────────────────────
    SECRET_KEY: str                                 # Must be a long random string in prod

    # ── Runtime ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"                # development | staging | production
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173"

    # ── Token lifetimes ───────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24

    # ── PIN security defaults (overridden at runtime by VenueSettings) ────────
    PIN_MAX_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 5

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/customers/google/callback"
    )

    # ── URLs ──────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Initial admin (seeded on first startup) ───────────────────────────────
    INITIAL_ADMIN_EMAIL: str = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: str = "ChangeMe123!"

    # ── Cookie behaviour ──────────────────────────────────────────────────────
    COOKIE_SECURE: bool = False          # Set True in production (HTTPS only)
    COOKIE_SAMESITE: str = "lax"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @computed_field
    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()