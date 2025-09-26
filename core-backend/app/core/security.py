"""
Security utilities for authentication and authorization.

This module provides JWT token handling, password hashing, and authentication utilities.
"""

import bcrypt
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration time

    Returns:
        JWT access token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration time

    Returns:
        JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Subject (user ID) if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != token_type:
            return None

        subject: str = payload.get("sub")
        if subject is None:
            return None

        return subject

    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def generate_salt() -> str:
    """
    Generate a random salt for password hashing.

    Returns:
        Random salt string
    """
    return bcrypt.gensalt().decode()


def authenticate_user(
    credentials: Dict[str, Any], verify_func
) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with credentials.

    Args:
        credentials: User credentials (email, password)
        verify_func: Function to verify user credentials

    Returns:
        User data if authentication successful, None otherwise
    """
    try:
        user = verify_func(credentials["email"])
        if not user:
            return None

        if not verify_password(credentials["password"], user["password_hash"]):
            return None

        return user

    except Exception:
        return None


def get_current_user(token: str = None) -> Optional[Dict[str, Any]]:
    """
    Get current user from JWT token.

    Args:
        token: JWT token from Authorization header

    Returns:
        User data if token is valid, None otherwise
    """
    if not token:
        return None

    subject = verify_token(token)
    if not subject:
        return None

    # This would typically fetch user from database
    # For now, return a mock user structure
    return {
        "id": subject,
        "email": f"user_{subject}@example.com",
        "is_active": True,
        "is_superuser": False,
    }


def require_auth(token: str = None) -> Dict[str, Any]:
    """
    Require authentication and return current user.

    Args:
        token: JWT token from Authorization header

    Returns:
        User data if authenticated

    Raises:
        HTTPException: If not authenticated
    """
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Require admin privileges.

    Args:
        user: User data from authentication

    Returns:
        User data if admin

    Raises:
        HTTPException: If not admin
    """
    if not user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return user


def get_token_from_header(authorization: str) -> str:
    """
    Extract token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Token string without Bearer prefix

    Raises:
        HTTPException: If header is invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing from authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def get_current_user_from_token(
    authorization: str = None, db_session=None
) -> dict:
    """
    Get current authenticated user from JWT token.

    Args:
        authorization: Authorization header value
        db_session: Database session for user lookup

    Returns:
        Dict with current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from authorization header
    token = get_token_from_header(authorization)

    # Verify token
    subject = verify_token(token)

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Get user from database using UserService
    from services.user_service import UserService

    user_service = UserService(db_session)
    user = await user_service.get_user_by_id(int(subject))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }
