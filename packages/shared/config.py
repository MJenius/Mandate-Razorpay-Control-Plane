"""Shared configuration and settings module using pydantic-settings."""

from functools import lru_cache

from pydantic import Field, model_validator
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
    PORT: int | None = Field(default=None, description="Cloud host dynamic PORT assignment")
    API_HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://mandate_user:mandate_secure_password@localhost:5433/mandate_db"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Production & Seeding Guardrails
    AUTO_SEED_DEMO: bool = Field(
        default=False,
        description="When True and in development/test, automatically seed demo agents if database is empty",
    )
    AUTO_MIGRATE_ON_STARTUP: bool = Field(
        default=True,
        description="In development/demo mode, automatically synchronize schema on startup",
    )

    # Razorpay Test Mode & Live API configuration
    RAZORPAY_KEY_ID: str = Field(default="rzp_test_placeholder", description="Razorpay Key ID")
    RAZORPAY_KEY_SECRET: str = Field(
        default="sample_secret_key_for_testing_purposes_only", description="Razorpay Key Secret"
    )
    RAZORPAY_WEBHOOK_SECRET: str = Field(
        default="sample_webhook_secret_key_for_testing", description="Razorpay Webhook Secret"
    )
    RAZORPAY_BASE_URL: str = Field(
        default="https://api.razorpay.com/v1", description="Razorpay API Base URL"
    )
    RAZORPAY_MOCK_MODE: bool = Field(
        default=False, description="When True, uses mock responses without live API calls"
    )

    # LLM Providers Configuration
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI Model Identifier")
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", description="Primary LLM provider")

    @property
    def server_port(self) -> int:
        """Effective listening port, prioritizing cloud provider $PORT over API_PORT."""
        return self.PORT if self.PORT is not None else self.API_PORT

    @property
    def cors_origins(self) -> list[str]:
        origins: list[str] = []
        for raw_origin in self.ALLOWED_ORIGINS.split(","):
            cleaned = raw_origin.strip().rstrip("/")
            if cleaned:
                origins.append(cleaned)
        return origins

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Strict production configuration invariants."""
        if self.ENVIRONMENT.lower() == "production":
            if self.AUTO_SEED_DEMO:
                raise ValueError("AUTO_SEED_DEMO cannot be enabled in production environment.")
            if self.RAZORPAY_MOCK_MODE:
                raise ValueError("RAZORPAY_MOCK_MODE must be False in production environment.")
            if self.SECRET_KEY.startswith("dev-secret-key"):
                raise ValueError("SECRET_KEY must be overridden with a secure key in production.")
        return self



@lru_cache
def get_settings() -> Settings:
    return Settings()
