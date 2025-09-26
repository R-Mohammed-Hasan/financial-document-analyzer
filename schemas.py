"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, validator


class TokenType(str, Enum):
    """Token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class UserRoleEnum(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    VIEWER = "viewer"
    ANALYST = "analyst"


class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Authentication Schemas
class Token(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Token data schema."""

    user_id: Optional[str] = None
    username: Optional[str] = None
    jti: Optional[str] = None


class UserCreate(BaseModel):
    """User creation schema."""

    username: str = Field(..., min_length=3, max_length=150, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")

    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
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


class UserLogin(BaseModel):
    """User login schema."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class UserUpdate(BaseModel):
    """User update schema."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """Password change schema."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """User response schema."""

    id: uuid.UUID
    username: str
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    roles: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response schema."""

    users: List[UserResponse]
    total: int
    page: int
    size: int


# Role and Permission Schemas
class PermissionResponse(BaseModel):
    """Permission response schema."""

    id: uuid.UUID
    resource: str
    action: str
    description: Optional[str]

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Role response schema."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    is_system_role: bool
    permissions: List[PermissionResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """Role creation schema."""

    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: List[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Role update schema."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[uuid.UUID]] = None


# Document Schemas
class DocumentResponse(BaseModel):
    """Document response schema."""

    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: Optional[str]
    file_size: int
    is_processed: bool
    processing_status: str
    created_at: datetime
    owner_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True


class DocumentUpload(BaseModel):
    """Document upload metadata schema."""

    filename: str
    content_type: Optional[str]
    file_size: int
    sha256_hash: str


class DocumentListResponse(BaseModel):
    """Document list response schema."""

    documents: List[DocumentResponse]
    total: int
    page: int
    size: int


# Analysis Schemas
class AnalysisRequest(BaseModel):
    """Analysis request schema."""

    query: str = Field(..., min_length=1, max_length=2000, description="Analysis query")
    analysis_type: str = Field(default="financial", description="Type of analysis")

    @validator("query")
    def validate_query(cls, v):
        """Validate query content."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class AnalysisResponse(BaseModel):
    """Analysis response schema."""

    id: uuid.UUID
    query: str
    analysis_result: str
    confidence_score: Optional[int]
    analysis_type: str
    status: str
    processing_time_seconds: Optional[int]
    created_at: datetime
    document_id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    """Analysis list response schema."""

    analyses: List[AnalysisResponse]
    total: int
    page: int
    size: int


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: uuid.UUID
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    created_at: datetime
    user_id: Optional[uuid.UUID]
    username: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response schema."""

    logs: List[AuditLogResponse]
    total: int
    page: int
    size: int


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    error: str = "Validation Error"
    detail: List[Dict[str, Any]]


# Health Check Schema
class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    timestamp: float
    version: str
    components: Dict[str, str]


# Rate Limit Schema
class RateLimitResponse(BaseModel):
    """Rate limit response schema."""

    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None


# Pagination Schema
class PaginationParams(BaseModel):
    """Pagination parameters schema."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


# Search Schema
class SearchParams(BaseModel):
    """Search parameters schema."""

    query: Optional[str] = Field(None, max_length=200, description="Search query")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(
        default="desc", regex="^(asc|desc)$", description="Sort order"
    )

    @validator("query")
    def validate_query(cls, v):
        """Validate search query."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v
