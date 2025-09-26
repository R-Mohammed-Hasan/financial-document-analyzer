"""
User Pydantic schemas for request/response models.

This module defines Pydantic models for user-related API endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    bio: Optional[str] = Field(None, description="User biography")
    role: str = Field("Viewer", description="User role (Viewer or Admin)")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="Password")

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for at least one uppercase, lowercase, and digit
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')

        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    profile_image: Optional[str] = Field(None, max_length=500)


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def password_strength(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')

        return v


class UserResponse(UserBase):
    """Schema for user response."""
    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Whether user is active")
    is_superuser: bool = Field(..., description="Whether user is admin")
    created_at: datetime = Field(..., description="Account creation date")
    updated_at: datetime = Field(..., description="Last update date")
    last_login: Optional[datetime] = Field(None, description="Last login date")
    profile_image: Optional[str] = Field(None, description="Profile image URL")
    full_name: str = Field(..., description="Full name")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for user list response."""
    id: int
    email: EmailStr
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserStatsResponse(BaseModel):
    """Schema for user statistics."""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    admin_users: int = Field(..., description="Number of admin users")
    new_users_today: int = Field(..., description="New users registered today")
    new_users_this_week: int = Field(..., description="New users this week")
    new_users_this_month: int = Field(..., description="New users this month")


class UserSearchResponse(BaseModel):
    """Schema for user search results."""
    users: List[UserListResponse] = Field(..., description="List of matching users")
    total: int = Field(..., description="Total number of matching users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of users per page")


class UserActivityResponse(BaseModel):
    """Schema for user activity information."""
    user_id: int
    email: EmailStr
    username: str
    last_login: Optional[datetime]
    login_count: int = Field(..., description="Total login count")
    files_uploaded: int = Field(..., description="Number of files uploaded")
    account_age_days: int = Field(..., description="Account age in days")
    is_online: bool = Field(..., description="Whether user is currently online")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
