"""Security utilities for authentication, authorization, and data protection."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import bleach
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from config import settings
from models import User, Role, Permission, RBACAction, UserRole, RolePermission

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class SecurityUtils:
    """Security utility functions."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Argon2."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "jti": str(uuid.uuid4()),
                "type": "access",
            }
        )

        return jwt.encode(
            to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def create_refresh_token() -> tuple[str, str]:
        """Create a refresh token and its hash."""
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def sanitize_input(value: str, allowed_tags: Optional[List[str]] = None) -> str:
        """Sanitize user input to prevent XSS attacks."""
        if allowed_tags is None:
            allowed_tags = []
        return bleach.clean(
            value, tags=allowed_tags, attributes={}, styles=[], strip=True
        )

    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """Validate password strength and return list of issues."""
        issues = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            issues.append(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
            )

        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one digit")

        if settings.PASSWORD_REQUIRE_SPECIAL_CHARS:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                issues.append("Password must contain at least one special character")

        return issues

    @staticmethod
    def generate_file_hash(content: bytes) -> str:
        """Generate SHA256 hash for file content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Validate if file extension is allowed."""
        if not filename:
            return False

        file_ext = filename.lower().split(".")[-1] if "." in filename else ""
        allowed_exts = [ext.lstrip(".") for ext in settings.ALLOWED_UPLOAD_EXTENSIONS]
        return file_ext in allowed_exts

    @staticmethod
    def validate_file_size(file_size: int) -> bool:
        """Validate if file size is within limits."""
        return file_size <= settings.MAX_UPLOAD_SIZE


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_roles(self, user_id: uuid.UUID) -> List[str]:
        """Get all role names for a user."""
        query = (
            select(Role.name)
            .join(UserRole)
            .where(and_(UserRole.user_id == user_id, Role.is_system_role == True))
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_user_permissions(self, user_id: uuid.UUID) -> List[Dict[str, str]]:
        """Get all permissions for a user through their roles."""
        query = (
            select(Permission.resource, Permission.action)
            .join(RolePermission)
            .join(Role)
            .join(UserRole)
            .where(and_(UserRole.user_id == user_id, Role.is_system_role == True))
        )
        result = await self.db.execute(query)
        return [
            {"resource": row[0], "action": row[1].value} for row in result.fetchall()
        ]

    async def has_permission(
        self, user_id: uuid.UUID, resource: str, action: RBACAction
    ) -> bool:
        """Check if user has specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return any(
            perm["resource"] == resource and perm["action"] == action.value
            for perm in permissions
        )

    async def has_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        """Check if user has specific role."""
        roles = await self.get_user_roles(user_id)
        return role_name in roles

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_name: str,
        assigned_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Assign a role to a user."""
        # Get role
        role_query = select(Role).where(Role.name == role_name)
        role_result = await self.db.execute(role_query)
        role = role_result.scalar_one_or_none()

        if not role:
            return False

        # Check if user already has this role
        existing_query = select(UserRole).where(
            and_(UserRole.user_id == user_id, UserRole.role_id == role.id)
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return True  # Already has role

        # Assign role
        user_role = UserRole(user_id=user_id, role_id=role.id, assigned_by=assigned_by)
        self.db.add(user_role)
        await self.db.commit()
        return True

    async def remove_role_from_user(self, user_id: uuid.UUID, role_name: str) -> bool:
        """Remove a role from a user."""
        # Get role
        role_query = select(Role).where(Role.name == role_name)
        role_result = await self.db.execute(role_query)
        role = role_result.scalar_one_or_none()

        if not role:
            return False

        # Remove role
        query = select(UserRole).where(
            and_(UserRole.user_id == user_id, UserRole.role_id == role.id)
        )
        result = await self.db.execute(query)
        user_role = result.scalar_one_or_none()

        if user_role:
            await self.db.delete(user_role)
            await self.db.commit()
            return True

        return False


class RateLimiter:
    """Rate limiting utility using Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        Returns (is_allowed, current_count)
        """
        current = await self.redis.get(key)

        if current is None:
            # First request in window
            await self.redis.setex(key, window_seconds, 1)
            return True, 1
        else:
            current_count = int(current)
            if current_count >= limit:
                return False, current_count
            else:
                # Increment counter
                new_count = await self.redis.incr(key)
                return True, new_count

    async def get_rate_limit_key(self, prefix: str, identifier: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{prefix}:{identifier}"

    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self.redis.delete(key)


# Global security utilities instance
security_utils = SecurityUtils()
