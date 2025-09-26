"""
Application configuration settings using Pydantic BaseSettings.

This module contains all configuration settings for the application,
loaded from environment variables with sensible defaults.
"""

import secrets
import os
from typing import List, Optional, Union
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Project metadata
    PROJECT_NAME: str = "Financial Document Analyzer"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for analyzing financial documents"
    API_V1_STR: str = "/api/v1"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://analyzer_user:analyzer_password@localhost:5432/financial_analyzer",
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30

    # Redis settings (for rate limiting and caching)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt"]

    # Email settings (for notifications)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@financial-analyzer.com"

    # External API settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return v or []

    @validator("ALLOWED_FILE_TYPES", pre=True)
    def assemble_file_types(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse allowed file types from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return v or []

    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Get allowed hosts for trusted host middleware."""
        return ["localhost", "127.0.0.1", "0.0.0.0"]

    class Config:
        """Pydantic configuration."""

        env_file = "core-backend/.env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
