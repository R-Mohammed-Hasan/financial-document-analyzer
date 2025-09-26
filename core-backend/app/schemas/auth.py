"""
Authentication Pydantic schemas for request/response models.

This module defines Pydantic models for authentication-related API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email address")


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    email: EmailStr = Field(..., description="Email address to verify")
    verification_code: str = Field(..., description="Verification code")


class ChangeEmailRequest(BaseModel):
    """Schema for changing email address."""

    new_email: EmailStr = Field(..., description="New email address")
    password: str = Field(..., description="Current password")


class TwoFactorSetupResponse(BaseModel):
    """Schema for 2FA setup response."""

    secret_key: str = Field(..., description="Secret key for 2FA setup")
    qr_code_url: str = Field(..., description="QR code URL for authenticator app")
    backup_codes: list[str] = Field(
        ..., description="Backup codes for account recovery"
    )


class TwoFactorVerifyRequest(BaseModel):
    """Schema for 2FA verification request."""

    verification_code: str = Field(..., description="6-digit verification code")
    backup_code: Optional[str] = Field(
        None, description="Backup code (if verification code fails)"
    )


class TwoFactorStatusResponse(BaseModel):
    """Schema for 2FA status response."""

    is_enabled: bool = Field(..., description="Whether 2FA is enabled")
    backup_codes_remaining: Optional[int] = Field(
        None, description="Number of backup codes remaining"
    )


class AuthResponse(BaseModel):
    """Schema for general authentication response."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    user_id: Optional[int] = Field(None, description="User ID if applicable")
    email: Optional[EmailStr] = Field(None, description="User email if applicable")


class LoginHistoryResponse(BaseModel):
    """Schema for login history response."""

    id: int = Field(..., description="Login record ID")
    user_id: int = Field(..., description="User ID")
    login_time: datetime = Field(..., description="Login timestamp")
    ip_address: str = Field(..., description="IP address")
    user_agent: str = Field(..., description="User agent string")
    location: Optional[str] = Field(None, description="Geographic location")
    successful: bool = Field(..., description="Whether login was successful")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class SessionInfoResponse(BaseModel):
    """Schema for session information response."""

    session_id: str = Field(..., description="Session ID")
    user_id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    ip_address: str = Field(..., description="IP address")
    user_agent: str = Field(..., description="User agent string")
    is_active: bool = Field(..., description="Whether session is active")


class LogoutResponse(BaseModel):
    """Schema for logout response."""

    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Logout message")


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    accept_terms: bool = Field(
        ..., description="Whether user accepts terms and conditions"
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v


class RegisterResponse(BaseModel):
    """Schema for user registration response."""

    success: bool = Field(..., description="Whether registration was successful")
    message: str = Field(..., description="Registration message")
    user_id: int = Field(..., description="New user ID")
    email: EmailStr = Field(..., description="User email")
    requires_verification: bool = Field(
        ..., description="Whether email verification is required"
    )


class OAuthLoginRequest(BaseModel):
    """Schema for OAuth login request."""

    provider: str = Field(..., description="OAuth provider (google, github, etc.)")
    access_token: str = Field(..., description="OAuth access token")
    code: Optional[str] = Field(None, description="Authorization code")


class OAuthLoginResponse(BaseModel):
    """Schema for OAuth login response."""

    success: bool = Field(..., description="Whether OAuth login was successful")
    access_token: Optional[str] = Field(None, description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: Optional[str] = Field("bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration time")
    is_new_user: bool = Field(..., description="Whether this is a new user")
    message: str = Field(..., description="Response message")
