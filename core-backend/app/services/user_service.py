"""
User service layer.

This module contains business logic for user management operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select
from datetime import datetime, timedelta

from db.models.user import User
from core.security import get_password_hash, verify_password
from schemas.user import UserCreate, UserUpdate
from core.logging_config import get_logger

# Module-level logger for the service layer
logger = get_logger(__name__)


class UserService:
    """
    Service class for user-related business logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the user service with a database session.

        Returns:
            None
        """
        self.db = db

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by their unique ID.

        Returns:
            The matching `User` instance if found, otherwise `None`.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if user:
            logger.debug(f"Fetched user by id: {user_id}")
        else:
            logger.debug(f"User not found by id: {user_id}")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Returns:
            The matching `User` instance if found, otherwise `None`.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        logger.debug(f"Lookup user by email: {email} | found={bool(user)}")
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Returns:
            The matching `User` instance if found, otherwise `None`.
        """
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        logger.debug(f"Lookup user by username: {username} | found={bool(user)}")
        return user

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """
        Get users with optional text search, active flag filtering, and pagination.

        Returns:
            List of `User` records matching the filters.
        """
        stmt = select(User)

        if search:
            search_filter = or_(
                User.email.contains(search),
                User.username.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search),
            )
            stmt = stmt.where(search_filter)

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        logger.debug(
            f"Fetched users | search={search!r} is_active={is_active} skip={skip} limit={limit} count={len(users)}"
        )
        return users

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create and persist a new user.

        Returns:
            The created `User` instance.
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            logger.warning(
                f"Create user failed: email already exists: {user_data.email}"
            )
            raise ValueError("User with this email already exists")

        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(
                f"Create user failed: username already exists: {user_data.username}"
            )
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
            role="Viewer",  # Default role for new users
        )

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        logger.info(f"User created | id={db_user.id} email={db_user.email}")
        return db_user

    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Update user fields that are provided in `user_data`.

        Returns:
            The updated `User` instance if the user exists, otherwise `None`.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Update user failed: not found | id={user_id}")
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

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"User updated | id={user.id}")
        return user

    async def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """
        Change the user's password after verifying the current password.

        Returns:
            True if the password was changed; False otherwise.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Change password failed: user not found | id={user_id}")
            return False

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            logger.warning(
                f"Change password failed: invalid current password | id={user_id}"
            )
            return False

        # Update password
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        logger.info(f"Password changed | id={user_id}")
        return True

    async def activate_user(self, user_id: int) -> bool:
        """
        Mark the user as active.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        await self.db.commit()
        logger.info(f"User activated | id={user_id}")
        return True

    async def deactivate_user(self, user_id: int) -> bool:
        """
        Mark the user as inactive.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        await self.db.commit()
        logger.info(f"User deactivated | id={user_id}")
        return True

    async def make_admin(self, user_id: int) -> bool:
        """
        Grant admin privileges (superuser) to the user.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_superuser = True
        await self.db.commit()
        logger.info(f"User granted admin | id={user_id}")
        return True

    async def remove_admin(self, user_id: int) -> bool:
        """
        Revoke admin privileges from the user and set role to Viewer.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_superuser = False
        user.role = "Viewer"
        await self.db.commit()
        logger.info(f"User admin revoked | id={user_id}")
        return True

    async def set_user_role(self, user_id: int, role: str) -> bool:
        """
        Set the user's role to either "Viewer" or "Admin".

        Returns:
            True if updated; False if the user does not exist or role invalid.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        if role not in ["Viewer", "Admin"]:
            return False

        user.set_role(role)
        await self.db.commit()
        logger.info(f"User role updated | id={user_id} role={role}")
        return True

    async def promote_to_admin(self, user_id: int) -> bool:
        """
        Promote a user to the admin role.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.promote_to_admin()
        await self.db.commit()
        logger.info(f"User promoted to admin | id={user_id}")
        return True

    async def demote_to_viewer(self, user_id: int) -> bool:
        """
        Demote a user to the viewer role.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.demote_to_viewer()
        await self.db.commit()
        logger.info(f"User demoted to viewer | id={user_id}")
        return True

    async def get_users_by_role(self, role: str) -> List[User]:
        """
        Get all users with a specific role.

        Returns:
            List of `User` records with the given role.
        """
        result = await self.db.execute(select(User).where(User.role == role))
        users = result.scalars().all()
        logger.debug(f"Fetched users by role | role={role} count={len(users)}")
        return users

    async def get_viewer_users(self) -> List[User]:
        """
        Get all users with role Viewer.

        Returns:
            List of `User` records with role Viewer.
        """
        result = await self.db.execute(select(User).where(User.role == "Viewer"))
        users = result.scalars().all()
        logger.debug(f"Fetched viewer users | count={len(users)}")
        return users

    async def update_last_login(self, user_id: int) -> bool:
        """
        Update the user's last_login timestamp to now.

        Returns:
            True if updated; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.last_login = datetime.utcnow()
        await self.db.commit()
        logger.info(f"User last_login updated | id={user_id}")
        return True

    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Aggregate and return user statistics such as totals and recent activity.

        Returns:
            Dictionary containing counts for users, actives, admins, and recents.
        """
        total_users = (await self.db.execute(select(func.count(User.id)))).scalar()
        active_users = (
            await self.db.execute(select(func.count(User.id)).where(User.is_active == True))
        ).scalar()
        admin_users = (
            await self.db.execute(select(func.count(User.id)).where(User.is_superuser == True))
        ).scalar()

        # New users today
        today = datetime.utcnow().date()
        new_users_today = (
            await self.db.execute(
                select(func.count(User.id)).where(func.date(User.created_at) == today)
            )
        ).scalar()

        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = (
            await self.db.execute(select(func.count(User.id)).where(User.created_at >= week_ago))
        ).scalar()

        # New users this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_users_month = (
            await self.db.execute(select(func.count(User.id)).where(User.created_at >= month_ago))
        ).scalar()

        stats = {
            "total_users": total_users,
            "active_users": active_users,
            "admin_users": admin_users,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_week,
            "new_users_this_month": new_users_month,
        }
        logger.debug(
            f"User stats | total={total_users} active={active_users} admins={admin_users}"
        )
        return stats

    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """
        Search users by name, email, or username.

        Returns:
            List of `User` records matching the search query (limited).
        """
        search_filter = or_(
            User.email.contains(query),
            User.username.contains(query),
            User.first_name.contains(query),
            User.last_name.contains(query),
        )
        stmt = select(User).where(search_filter).limit(limit)
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        logger.debug(f"Search users | query={query!r} limit={limit} count={len(users)}")
        return users

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user account by ID.

        Returns:
            True if deleted; False if the user does not exist.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Delete user failed: not found | id={user_id}")
            return False

        await self.db.delete(user)
        await self.db.commit()
        logger.info(f"User deleted | id={user_id}")
        return True

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user using email and password.

        Returns:
            The `User` if authentication passes; otherwise `None`.
        """
        user = await self.get_user_by_email(email)
        if not user:
            logger.debug(f"Authentication failed: user not found | email={email}")
            return None

        if not verify_password(password, user.password_hash):
            logger.debug(f"Authentication failed: invalid password | email={email}")
            return None

        if not user.is_active:
            logger.info(f"Authentication blocked: inactive user | id={user.id}")
            return None

        logger.info(f"Authentication success | id={user.id}")
        return user

    async def get_recent_users(self, days: int = 30) -> List[User]:
        """
        Get users created within the last N days.

        Returns:
            List of recent `User` records.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(select(User).where(User.created_at >= cutoff_date))
        users = result.scalars().all()
        logger.debug(f"Recent users | days={days} count={len(users)}")
        return users

    async def get_inactive_users(self, days: int = 90) -> List[User]:
        """
        Get users who have not logged in for at least N days.

        Returns:
            List of inactive `User` records.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(User).where(or_(User.last_login.is_(None), User.last_login < cutoff_date))
        )
        users = result.scalars().all()
        logger.debug(f"Inactive users | days={days} count={len(users)}")
        return users
