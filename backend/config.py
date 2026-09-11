"""
LabelSure — Configuration
All settings are environment-variable driven.
No secret values live here — every sensitive field MUST be set via env var.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Database ──────────────────────────────────────────────────────────────
    # REQUIRED in production. For local dev only, falls back to SQLite.
    # Production example: postgresql+asyncpg://user:pass@host:5432/dbname
    database_url: str = "sqlite+aiosqlite:///./labelsure.db"

    # Connection pool settings (ignored for SQLite)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800  # recycle connections every 30 min

    # ─── Security ──────────────────────────────────────────────────────────────
    # REQUIRED in production — generate with:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    # There is intentionally NO default here in production mode.
    # A missing / weak key is caught by the validator below.
    secret_key: str = ""

    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # ─── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, or "*" for dev only.
    # Example: "https://dashboard.labelsure.app,https://labelsure.app"
    cors_origins: str = "*"

    # ─── Rate limiting ─────────────────────────────────────────────────────────
    # Requests per minute per IP on /auth endpoints
    rate_limit_auth_rpm: int = 20
    # Requests per minute per authenticated user on /scans/upload
    rate_limit_upload_rpm: int = 30

    # ─── File uploads ──────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    # ─── OCR / CV ──────────────────────────────────────────────────────────────
    ocr_confidence_threshold: float = 0.70
    cv_dpi_default: float = 150.0

    # ─── App ───────────────────────────────────────────────────────────────────
    app_name: str = "LabelSure"
    version: str = "1.0.0"
    # Set to False in production — controls SQLAlchemy echo and /docs exposure
    debug: bool = False

    # ─── Structured logging ────────────────────────────────────────────────────
    # "json" for production log aggregators (Datadog, Papertrail, etc.)
    # "text" for local development
    log_format: Literal["json", "text"] = "text"

    # ─── Workers (informational — used by gunicorn start command) ──────────────
    workers: int = 2

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        # Allow empty only during pytest
        import sys
        if "pytest" in sys.modules:
            return v or "test-secret-key-not-for-production"
        if not v:
            raise ValueError(
                "SECRET_KEY is not set. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if v in (
            "changeme-use-a-long-random-secret-in-production",
            "changeme-in-production",
            "secret",
            "password",
        ):
            raise ValueError(
                "SECRET_KEY is set to a known insecure placeholder. "
                "Generate a real key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters.")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS into a list."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Prevent extra keys from causing silent failures
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
