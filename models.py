"""Database models for the Financial Document Analyzer."""

import uuid
import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import text

from config import settings

# Database setup
engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


class RBACAction(enum.Enum):
    """Available RBAC actions."""

    read = "read"
    write = "write"
    delete = "delete"
    manage = "manage"


class UserRoleEnum(enum.Enum):
    """Predefined user roles."""

    admin = "admin"
    viewer = "viewer"
    analyst = "analyst"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    password_hash = Column(String(512), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
    analyses = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_username_active", "username", "is_active"),
    )


class Role(Base):
    """Role model for RBAC."""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    users = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base):
    """Permission model for RBAC."""

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource = Column(String(100), nullable=False, index=True)
    action = Column(Enum(RBACAction), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    roles = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    # Unique constraint
    __table_args__ = (
        Index("idx_permission_resource_action", "resource", "action", unique=True),
    )


class RolePermission(Base):
    """Many-to-many relationship between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class UserRole(Base):
    """Many-to-many relationship between users and roles."""

    __tablename__ = "user_roles"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="users")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class RefreshToken(Base):
    """Refresh token model for JWT token management."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(256), nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_info = Column(Text, nullable=True)  # Store device/browser info

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_refresh_token_user_active", "user_id", "revoked_at"),
        Index("idx_refresh_token_expires", "expires_at"),
    )


class Document(Base):
    """Document model for storing uploaded financial documents."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    filename = Column(String(512), nullable=False)
    original_filename = Column(String(512), nullable=False)
    content_type = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(1024), nullable=False)
    sha256_hash = Column(String(128), nullable=False, index=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", back_populates="documents")
    analyses = relationship(
        "Analysis", back_populates="document", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_document_user_created", "user_id", "created_at"),
        Index("idx_document_status", "processing_status"),
    )


class Analysis(Base):
    """Analysis model for storing analysis results."""

    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    query = Column(Text, nullable=False)
    analysis_result = Column(Text, nullable=False)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    analysis_type = Column(String(100), nullable=False, default="financial")
    status = Column(String(50), default="completed", nullable=False)
    processing_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="analyses")
    document = relationship("Document", back_populates="analyses")

    # Indexes
    __table_args__ = (
        Index("idx_analysis_user_created", "user_id", "created_at"),
        Index("idx_analysis_document", "document_id"),
        Index("idx_analysis_type", "analysis_type"),
    )


class AuditLog(Base):
    """Audit log model for tracking system activities."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_action_created", "action", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


# Database session dependency
async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Database initialization
async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
