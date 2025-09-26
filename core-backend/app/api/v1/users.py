"""
Users API router.

This module defines user management API endpoints including user CRUD operations,
profile management, and user administration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_async_db
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
    # Mock implementation - replace with actual database queries
    mock_users = [
        UserListResponse(
            id=1,
            email="user1@example.com",
            username="user1",
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            is_active=True,
            is_superuser=False,
            created_at="2023-01-01T00:00:00",
            last_login="2023-12-01T10:00:00",
        ),
        UserListResponse(
            id=2,
            email="admin@example.com",
            username="admin",
            first_name="Jane",
            last_name="Smith",
            full_name="Jane Smith",
            is_active=True,
            is_superuser=True,
            created_at="2023-01-01T00:00:00",
            last_login="2023-12-01T11:00:00",
        ),
    ]

    # Filter by search query
    if search:
        search_lower = search.lower()
        mock_users = [
            user
            for user in mock_users
            if (
                search_lower in user.email.lower()
                or search_lower in user.username.lower()
                or search_lower in user.full_name.lower()
            )
        ]

    # Filter by active status
    if is_active is not None:
        mock_users = [user for user in mock_users if user.is_active == is_active]

    # Apply pagination
    total = len(mock_users)
    users = mock_users[skip : skip + limit]

    return UserSearchResponse(
        users=users, total=total, page=skip // limit + 1, page_size=limit
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
    # Mock implementation - replace with actual database query
    if user_id == 1:
        return UserResponse(
            id=1,
            email="user1@example.com",
            username="user1",
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            is_active=True,
            is_superuser=False,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-12-01T10:00:00",
            last_login="2023-12-01T10:00:00",
            profile_image=None,
        )
    elif user_id == 2:
        return UserResponse(
            id=2,
            email="admin@example.com",
            username="admin",
            first_name="Jane",
            last_name="Smith",
            full_name="Jane Smith",
            is_active=True,
            is_superuser=True,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-12-01T11:00:00",
            last_login="2023-12-01T11:00:00",
            profile_image=None,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
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
    # Mock implementation - replace with actual database update
    if user_id == 1:
        return UserResponse(
            id=1,
            email="user1@example.com",
            username="user1",
            first_name=user_update.first_name or "John",
            last_name=user_update.last_name or "Doe",
            full_name=f"{user_update.first_name or 'John'} {user_update.last_name or 'Doe'}",
            is_active=True,
            is_superuser=False,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-12-01T10:00:00",
            last_login="2023-12-01T10:00:00",
            profile_image=user_update.profile_image,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
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
    # Mock implementation - replace with actual database deletion
    if user_id in [1, 2]:
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


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
    # Mock implementation - replace with actual database update
    if user_id in [1, 2]:
        return {"message": "User activated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


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
    # Mock implementation - replace with actual database update
    if user_id in [1, 2]:
        return {"message": "User deactivated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


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
    # Mock implementation - replace with actual database queries
    if user_id == 1:
        return UserActivityResponse(
            user_id=1,
            email="user1@example.com",
            username="user1",
            last_login="2023-12-01T10:00:00",
            login_count=150,
            files_uploaded=25,
            account_age_days=365,
            is_online=False,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
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
    # Mock implementation - replace with actual database aggregation
    return UserStatsResponse(
        total_users=100,
        active_users=95,
        admin_users=5,
        new_users_today=3,
        new_users_this_week=15,
        new_users_this_month=45,
    )


@router.get("/users/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: dict = Depends(lambda: {"id": 1}),  # Mock current user
) -> UserResponse:
    """
    Get current user's profile.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse with current user profile
    """
    # Mock implementation - replace with actual database query
    return UserResponse(
        id=1,
        email="user1@example.com",
        username="user1",
        first_name="John",
        last_name="Doe",
        full_name="John Doe",
        is_active=True,
        is_superuser=False,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-12-01T10:00:00",
        last_login="2023-12-01T10:00:00",
        profile_image=None,
    )


@router.put("/users/me/profile", response_model=UserResponse)
async def update_my_profile(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(lambda: {"id": 1}),  # Mock current user
) -> UserResponse:
    """
    Update current user's profile.

    Args:
        profile_update: Profile update data
        current_user: Current authenticated user

    Returns:
        UserResponse with updated profile
    """
    # Mock implementation - replace with actual database update
    return UserResponse(
        id=1,
        email="user1@example.com",
        username="user1",
        first_name=profile_update.first_name or "John",
        last_name=profile_update.last_name or "Doe",
        full_name=f"{profile_update.first_name or 'John'} {profile_update.last_name or 'Doe'}",
        is_active=True,
        is_superuser=False,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-12-01T10:00:00",
        last_login="2023-12-01T10:00:00",
        profile_image=None,
    )
