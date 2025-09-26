"""
User service layer.

This module contains business logic for user management operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta

from db.models.user import User
from core.security import get_password_hash, verify_password
from schemas.user import UserCreate, UserUpdate


class UserService:
    """
    Service class for user-related business logic.
    """

    def __init__(self, db: Session):
        """Initialize user service with database session."""
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """Get users with optional filtering and pagination."""
        query = self.db.query(User)

        if search:
            search_filter = or_(
                User.email.contains(search),
                User.username.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search),
            )
            query = query.filter(search_filter)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")

        existing_user = self.get_user_by_username(user_data.username)
        if existing_user:
            raise ValueError("User with this username already exists")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            bio=user_data.bio,
            is_active=True,
            is_superuser=False,
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Update fields if provided
        if user_data.first_name is not None:
            user.first_name = user_data.first_name
        if user_data.last_name is not None:
            user.last_name = user_data.last_name
        if user_data.phone_number is not None:
            user.phone_number = user_data.phone_number
        if user_data.bio is not None:
            user.bio = user_data.bio
        if user_data.profile_image is not None:
            user.profile_image = user_data.profile_image

        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """Change user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False

        # Update password
        user.password_hash = get_password_hash(new_password)
        self.db.commit()

        return True

    def activate_user(self, user_id: int) -> bool:
        """Activate user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        self.db.commit()

        return True

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        self.db.commit()

        return True

    def make_admin(self, user_id: int) -> bool:
        """Grant admin privileges to user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_superuser = True
        self.db.commit()

        return True

    def remove_admin(self, user_id: int) -> bool:
        """Remove admin privileges from user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_superuser = False
        self.db.commit()

        return True

    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.last_login = datetime.utcnow()
        self.db.commit()

        return True

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        total_users = self.db.query(func.count(User.id)).scalar()
        active_users = (
            self.db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        )
        admin_users = (
            self.db.query(func.count(User.id))
            .filter(User.is_superuser == True)
            .scalar()
        )

        # New users today
        today = datetime.utcnow().date()
        new_users_today = (
            self.db.query(func.count(User.id))
            .filter(func.date(User.created_at) == today)
            .scalar()
        )

        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = (
            self.db.query(func.count(User.id))
            .filter(User.created_at >= week_ago)
            .scalar()
        )

        # New users this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_users_month = (
            self.db.query(func.count(User.id))
            .filter(User.created_at >= month_ago)
            .scalar()
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "admin_users": admin_users,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_week,
            "new_users_this_month": new_users_month,
        }

    def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Search users by name, email, or username."""
        search_filter = or_(
            User.email.contains(query),
            User.username.contains(query),
            User.first_name.contains(query),
            User.last_name.contains(query),
        )

        return self.db.query(User).filter(search_filter).limit(limit).all()

    def delete_user(self, user_id: int) -> bool:
        """Delete user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()

        return True

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    def get_recent_users(self, days: int = 30) -> List[User]:
        """Get users created in the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(User).filter(User.created_at >= cutoff_date).all()

    def get_inactive_users(self, days: int = 90) -> List[User]:
        """Get users who haven't logged in for N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(User)
            .filter(or_(User.last_login.is_(None), User.last_login < cutoff_date))
            .all()
        )
