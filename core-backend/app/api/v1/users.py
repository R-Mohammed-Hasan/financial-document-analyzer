"""
Users API router.

This module defines user management API endpoints including user CRUD operations,
profile management, and user administration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.orm import selectinload

from db.session import get_async_db
from db.models.user import User
from schemas.user import (
    UserResponse,
    UserListResponse,
    UserUpdate,
    UserProfileUpdate,
    UserStatsResponse,
    UserSearchResponse,
    UserActivityResponse,
)

router = APIRouter()


@router.get("/users", response_model=UserSearchResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of users to return"),
    search: Optional[str] = Query(None, description="Search query for users"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_async_db),
) -> UserSearchResponse:
    """
    List users with pagination and filtering.

    Args:
        skip: Number of users to skip
        limit: Number of users to return
        search: Search query for users
        is_active: Filter by active status
        db: Database session

    Returns:
        UserSearchResponse with paginated user list
    """
    # Build the base query
    query = db.query(User)

    # Apply search filter
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    # Apply active status filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = await db.scalar(query.with_entities(func.count(User.id)))

    # Apply pagination and ordering
    users = await db.execute(
        query.order_by(desc(User.created_at))
        .offset(skip)
        .limit(limit)
    )
    users = users.scalars().all()

    # Convert to response format
    user_responses = [
        UserListResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )
        for user in users
    ]

    return UserSearchResponse(
        users=user_responses,
        total=total or 0,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)) -> UserResponse:
    """
    Get user by ID.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        UserResponse with user data
    """
    # Query user from database
    user = await db.get(User, user_id)

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
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        profile_image=user.profile_image,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_async_db)
) -> UserResponse:
    """
    Update user information.

    Args:
        user_id: User ID
        user_update: User update data
        db: Database session

    Returns:
        UserResponse with updated user data
    """
    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user fields if provided
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    # Update the updated_at timestamp
    from datetime import datetime
    user.updated_at = datetime.utcnow()

    # Commit changes
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        profile_image=user.profile_image,
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_db)) -> dict:
    """
    Delete user account.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Dict with deletion status
    """
    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Delete user from database
    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/activate")
async def activate_user(user_id: int, db: AsyncSession = Depends(get_async_db)) -> dict:
    """
    Activate user account.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Dict with activation status
    """
    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Activate user
    user.activate()
    await db.commit()

    return {"message": "User activated successfully"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(user_id: int, db: AsyncSession = Depends(get_async_db)) -> dict:
    """
    Deactivate user account.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Dict with deactivation status
    """
    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Deactivate user
    user.deactivate()
    await db.commit()

    return {"message": "User deactivated successfully"}


@router.get("/users/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: int, db: AsyncSession = Depends(get_async_db)
) -> UserActivityResponse:
    """
    Get user activity information.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        UserActivityResponse with user activity data
    """
    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Calculate account age in days
    from datetime import datetime
    account_age_days = (datetime.utcnow() - user.created_at.replace(tzinfo=None)).days if user.created_at else 0

    # Get files uploaded count
    from db.models.file import File
    files_uploaded = await db.scalar(
        db.query(func.count(File.id)).filter(File.user_id == user_id)
    )

    # For now, we'll use mock data for login_count and is_online
    # In a real implementation, you'd track these in separate tables
    login_count = 150  # This would come from a user sessions table
    is_online = False  # This would be determined by recent activity

    return UserActivityResponse(
        user_id=user.id,
        email=user.email,
        username=user.username,
        last_login=user.last_login.isoformat() if user.last_login else None,
        login_count=login_count,
        files_uploaded=files_uploaded or 0,
        account_age_days=account_age_days,
        is_online=is_online,
    )


@router.get("/users/stats/overview", response_model=UserStatsResponse)
async def get_user_stats(db: AsyncSession = Depends(get_async_db)) -> UserStatsResponse:
    """
    Get user statistics overview.

    Args:
        db: Database session

    Returns:
        UserStatsResponse with user statistics
    """
    from datetime import datetime, timedelta

    # Get total users count
    total_users = await db.scalar(db.query(func.count(User.id)))

    # Get active users count
    active_users = await db.scalar(
        db.query(func.count(User.id)).filter(User.is_active == True)
    )

    # Get admin users count
    admin_users = await db.scalar(
        db.query(func.count(User.id)).filter(User.is_superuser == True)
    )

    # Get new users today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = await db.scalar(
        db.query(func.count(User.id)).filter(User.created_at >= today_start)
    )

    # Get new users this week
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_this_week = await db.scalar(
        db.query(func.count(User.id)).filter(User.created_at >= week_start)
    )

    # Get new users this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = await db.scalar(
        db.query(func.count(User.id)).filter(User.created_at >= month_start)
    )

    return UserStatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        admin_users=admin_users or 0,
        new_users_today=new_users_today or 0,
        new_users_this_week=new_users_this_week or 0,
        new_users_this_month=new_users_this_month or 0,
    )


@router.get("/users/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: dict = Depends(lambda: {"id": 1}),  # Mock current user - replace with proper auth dependency
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """
    Get current user's profile.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse with current user profile
    """
    # Extract user ID from current_user (this would come from auth token in real implementation)
    user_id = current_user.get("id")  # In real implementation, this would be extracted from JWT

    # Get user from database
    user = await db.get(User, user_id)
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
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        profile_image=user.profile_image,
    )


@router.put("/users/me/profile", response_model=UserResponse)
async def update_my_profile(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(lambda: {"id": 1}),  # Mock current user - replace with proper auth dependency
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """
    Update current user's profile.

    Args:
        profile_update: Profile update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse with updated profile
    """
    # Extract user ID from current_user (this would come from auth token in real implementation)
    user_id = current_user.get("id")  # In real implementation, this would be extracted from JWT

    # Get user from database
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user fields if provided (only profile-related fields)
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    # Update the updated_at timestamp
    from datetime import datetime
    user.updated_at = datetime.utcnow()

    # Commit changes
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        profile_image=user.profile_image,
    )
