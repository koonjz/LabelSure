"""
LabelSure — Configuration
Reads from .env file via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://labelsure:labelsure@localhost:5432/labelsure"
    sync_database_url: str = "postgresql://labelsure:labelsure@localhost:5432/labelsure"

    # JWT
    secret_key: str = "changeme-use-a-long-random-secret-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # File storage
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    # OCR / CV settings
    ocr_confidence_threshold: float = 0.7  # below this → needs_manual_review
    cv_dpi_default: float = 150.0          # assumed DPI for geometry calcs

    # App
    app_name: str = "LabelSure"
    version: str = "1.0.0"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
