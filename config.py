"""Configuration management for the Financial Document Analyzer."""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/financial_analyzer",
        env="DATABASE_URL",
        description="Database connection URL",
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL for caching and rate limiting",
    )

    # JWT Configuration
    JWT_SECRET: str = Field(
        ..., env="JWT_SECRET", description="Secret key for JWT token signing"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256", env="JWT_ALGORITHM", description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token expiration time in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        env="REFRESH_TOKEN_EXPIRE_DAYS",
        description="Refresh token expiration time in days",
    )

    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        env="MAX_UPLOAD_SIZE",
        description="Maximum file upload size in bytes",
    )
    ALLOWED_UPLOAD_EXTENSIONS: str = Field(
        default=".pdf,.txt,.doc,.docx",
        env="ALLOWED_UPLOAD_EXTENSIONS",
        description="Allowed file extensions for upload (comma-separated)",
    )
    UPLOAD_DIR: str = Field(
        default="data",
        env="UPLOAD_DIR",
        description="Directory for storing uploaded files",
    )

    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        env="RATE_LIMIT_REQUESTS",
        description="Number of requests allowed per window",
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=3600,  # 1 hour
        env="RATE_LIMIT_WINDOW_SECONDS",
        description="Rate limiting window in seconds",
    )
    UPLOAD_RATE_LIMIT: int = Field(
        default=10,
        env="UPLOAD_RATE_LIMIT",
        description="Number of uploads allowed per window",
    )
    UPLOAD_RATE_WINDOW_SECONDS: int = Field(
        default=3600,  # 1 hour
        env="UPLOAD_RATE_WINDOW_SECONDS",
        description="Upload rate limiting window in seconds",
    )

    # Security Configuration
    PASSWORD_MIN_LENGTH: int = Field(
        default=8, env="PASSWORD_MIN_LENGTH", description="Minimum password length"
    )
    PASSWORD_REQUIRE_SPECIAL_CHARS: bool = Field(
        default=True,
        env="PASSWORD_REQUIRE_SPECIAL_CHARS",
        description="Require special characters in passwords",
    )

    # API Configuration
    API_V1_PREFIX: str = Field(
        default="/api/v1", env="API_V1_PREFIX", description="API version 1 prefix"
    )

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS",
        env_parse_json=True,
        description="Allowed CORS origins",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL", description="Logging level")

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(
        ..., env="OPENAI_API_KEY", description="OpenAI API key for LLM operations"
    )

    @property
    def allowed_upload_extensions_list(self) -> List[str]:
        """Get allowed upload extensions as a list."""
        if isinstance(self.ALLOWED_UPLOAD_EXTENSIONS, str):
            return [ext.strip() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")]
        return self.ALLOWED_UPLOAD_EXTENSIONS





    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong enough."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
