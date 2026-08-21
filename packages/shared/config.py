"""Shared configuration and settings module using pydantic-settings."""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # API
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mandate_user:mandate_secure_password@localhost:5432/mandate_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Razorpay (Test Mode credentials default for mock safety)
    RAZORPAY_KEY_ID: str = Field(default="rzp_test_placeholder", description="Razorpay Test Key ID")
    RAZORPAY_KEY_SECRET: str = Field(default="placeholder_secret", description="Razorpay Test Secret")
    RAZORPAY_WEBHOOK_SECRET: str = Field(default="webhook_placeholder_secret", description="Razorpay Webhook Secret")
    RAZORPAY_MOCK_MODE: bool = Field(default=True, description="When True, allows test runs without live API calls")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
