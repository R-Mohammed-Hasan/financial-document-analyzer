"""FastAPI dependencies for authentication, authorization, and rate limiting."""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import aioredis
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from config import settings
from models import User, get_db, RefreshToken
from security import security_utils, RBACManager, RateLimiter
from schemas import TokenData, UserRoleEnum

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


# Redis connection
redis_client = None


async def get_redis():
    """Get Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(settings.REDIS_URL)
    return redis_client


async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    redis = await get_redis()
    return RateLimiter(redis)


# Authentication Dependencies
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security_utils.verify_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

    except HTTPException:
        raise credentials_exception

    # Get user from database
    query = select(User).where(
        and_(User.id == uuid.UUID(user_id), User.is_active == True)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current verified user."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User not verified"
        )
    return current_user


# Authorization Dependencies
def require_roles(required_roles: List[str]):
    """Dependency factory for role-based authorization."""

    async def _require_roles(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        rbac_manager = RBACManager(db)
        user_roles = await rbac_manager.get_user_roles(current_user.id)

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}",
            )

        return current_user

    return _require_roles


def require_permissions(resource: str, action: str):
    """Dependency factory for permission-based authorization."""

    async def _require_permissions(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        from models import RBACAction

        rbac_manager = RBACManager(db)
        has_permission = await rbac_manager.has_permission(
            current_user.id, resource, RBACAction(action)
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {action} on {resource}",
            )

        return current_user

    return _require_permissions


# Predefined role dependencies
require_admin = require_roles([UserRoleEnum.ADMIN.value])
require_viewer = require_roles([UserRoleEnum.VIEWER.value, UserRoleEnum.ADMIN.value])
require_analyst = require_roles([UserRoleEnum.ANALYST.value, UserRoleEnum.ADMIN.value])


# Rate Limiting Dependencies
async def rate_limit(
    request: Request,
    limit: int = settings.RATE_LIMIT_REQUESTS,
    window_seconds: int = settings.RATE_LIMIT_WINDOW_SECONDS,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Rate limiting dependency."""
    # Get client identifier (IP address or user ID if authenticated)
    client_ip = request.client.host if request.client else "unknown"

    # Try to get user ID from token if available
    user_id = None
    try:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = security_utils.verify_token(token)
            user_id = payload.get("sub")
    except:
        pass

    # Use user ID if available, otherwise use IP
    identifier = user_id if user_id else client_ip
    key = await rate_limiter.get_rate_limit_key("api", identifier)

    is_allowed, current_count = await rate_limiter.check_rate_limit(
        key, limit, window_seconds
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit} requests per {window_seconds} seconds",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(
                    int(datetime.utcnow().timestamp()) + window_seconds
                ),
                "Retry-After": str(window_seconds),
            },
        )

    # Add rate limit headers to response
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(limit - current_count),
        "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + window_seconds),
    }


async def upload_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Upload-specific rate limiting dependency."""
    identifier = str(current_user.id)
    key = await rate_limiter.get_rate_limit_key("upload", identifier)

    is_allowed, current_count = await rate_limiter.check_rate_limit(
        key, settings.UPLOAD_RATE_LIMIT, settings.UPLOAD_RATE_WINDOW_SECONDS
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Upload rate limit exceeded. Limit: {settings.UPLOAD_RATE_LIMIT} uploads per {settings.UPLOAD_RATE_WINDOW_SECONDS} seconds",
            headers={
                "X-RateLimit-Limit": str(settings.UPLOAD_RATE_LIMIT),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(
                    int(datetime.utcnow().timestamp())
                    + settings.UPLOAD_RATE_WINDOW_SECONDS
                ),
                "Retry-After": str(settings.UPLOAD_RATE_WINDOW_SECONDS),
            },
        )

    # Add rate limit headers to response
    request.state.upload_rate_limit_headers = {
        "X-RateLimit-Limit": str(settings.UPLOAD_RATE_LIMIT),
        "X-RateLimit-Remaining": str(settings.UPLOAD_RATE_LIMIT - current_count),
        "X-RateLimit-Reset": str(
            int(datetime.utcnow().timestamp()) + settings.UPLOAD_RATE_WINDOW_SECONDS
        ),
    }


# Optional authentication (for endpoints that work with or without auth)
async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# Database transaction dependency
async def get_db_transaction(db: AsyncSession = Depends(get_db)):
    """Get database session with transaction support."""
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


# Request context dependency
async def get_request_context(request: Request):
    """Get request context information."""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": getattr(request.state, "request_id", None),
    }


# Audit logging dependency
async def audit_log(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    request_context: Dict[str, Any] = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Audit logging dependency."""
    from models import AuditLog

    audit_entry = AuditLog(
        user_id=current_user.id if current_user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request_context.get("ip_address"),
        user_agent=request_context.get("user_agent"),
        success=True,
    )

    db.add(audit_entry)
    await db.commit()

    return audit_entry
