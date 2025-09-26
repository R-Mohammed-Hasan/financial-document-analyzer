"""
Authentication API router.

This module defines authentication-related API endpoints including login, logout,
token refresh, password reset, and user registration.
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm


from core.config import settings
from core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
)
from db.session import get_async_db
from services.user_service import UserService
from schemas.auth import (
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    RegisterRequest,
    RegisterResponse,
    AuthResponse,
    LogoutResponse,
)
from schemas.user import UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_async_db)) -> TokenResponse:
    """
    Authenticate user and return access and refresh tokens.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        TokenResponse with access and refresh tokens
    """
    # Use UserService for authentication
    user_service = UserService(db)
    user = await user_service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated"
        )

    # Update last login
    await user_service.update_last_login(user.id)

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request

    Returns:
        TokenRefreshResponse with new access token
    """
    subject = verify_token(request.refresh_token, "refresh")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=subject, expires_delta=access_token_expires
    )

    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest, db: AsyncSession = Depends(get_async_db)
) -> RegisterResponse:
    """
    Register a new user account.

    Args:
        request: Registration data
        db: Database session

    Returns:
        RegisterResponse with registration status
    """
    # Use UserService for user creation
    user_service = UserService(db)

    try:
        # Create user data object
        from schemas.user import UserCreate

        user_data = UserCreate(
            email=request.email,
            username=request.username,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            phone_number=None,
            bio=None,
        )

        # Create the user
        user = await user_service.create_user(user_data)

        return RegisterResponse(
            success=True,
            message="User registered successfully",
            user_id=user.id,
            email=user.email,
            requires_verification=False,  # No email verification needed
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", response_model=LogoutResponse)
async def logout() -> LogoutResponse:
    """
    Logout user (client-side token removal).

    Returns:
        LogoutResponse with logout status
    """
    # In a real implementation, you might want to:
    # 1. Add the token to a blacklist
    # 2. Log the logout event
    # 3. Clean up user sessions

    return LogoutResponse(success=True, message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(
        lambda x: x.headers.get("Authorization", "").replace("Bearer ", "")
    ),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        UserResponse with current user data
    """
    subject = verify_token(token)

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Get user from database
    user_service = UserService(db)
    user = await user_service.get_user_by_id(int(subject))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        profile_image=user.profile_image,
        phone_number=user.phone_number,
        bio=user.bio,
    )
