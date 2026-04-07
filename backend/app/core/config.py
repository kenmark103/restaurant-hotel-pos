from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/customers/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    INITIAL_ADMIN_EMAIL: str = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: str = "ChangeMe123!"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field
    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
