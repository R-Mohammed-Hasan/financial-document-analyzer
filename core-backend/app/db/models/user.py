"""
User database model.

This module defines the User SQLAlchemy model for user management.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, or_
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.base import Base


class User(Base):
    """
    User model for storing user information.

    Attributes:
        id: Primary key
        email: User email address (unique)
        username: Username (unique)
        password_hash: Hashed password
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user is active
        is_superuser: Whether the user has admin privileges
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last login timestamp
        profile_image: URL to profile image
        phone_number: User's phone number
        bio: User biography
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), default="Viewer", nullable=False)  # "Viewer" or "Admin"
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login = Column(DateTime(timezone=True), nullable=True)
    profile_image = Column(String(500), nullable=True)
    phone_number = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)

    # Relationships
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    financial_analyses = relationship("FinancialAnalysis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.is_superuser or self.role == "Admin"

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "profile_image": self.profile_image,
            "phone_number": self.phone_number,
            "bio": self.bio,
        }

    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False

    def make_admin(self) -> None:
        """Grant admin privileges to the user."""
        self.is_superuser = True

    def remove_admin(self) -> None:
        """Remove admin privileges from the user."""
        self.is_superuser = False

    def set_role(self, role: str) -> None:
        """Set user role (Viewer or Admin)."""
        if role in ["Viewer", "Admin"]:
            self.role = role
            if role == "Admin":
                self.is_superuser = True
            else:
                self.is_superuser = False

    def promote_to_admin(self) -> None:
        """Promote user to admin role."""
        self.role = "Admin"
        self.is_superuser = True

    def demote_to_viewer(self) -> None:
        """Demote user to viewer role."""
        self.role = "Viewer"
        self.is_superuser = False

    @classmethod
    def get_by_email(cls, db_session, email: str):
        """Get user by email address."""
        return db_session.query(cls).filter(cls.email == email).first()

    @classmethod
    def get_by_username(cls, db_session, username: str):
        """Get user by username."""
        return db_session.query(cls).filter(cls.username == username).first()

    @classmethod
    def get_active_users(cls, db_session):
        """Get all active users."""
        return db_session.query(cls).filter(cls.is_active == True).all()

    @classmethod
    def get_admin_users(cls, db_session):
        """Get all admin users."""
        return db_session.query(cls).filter(
            or_(cls.is_superuser == True, cls.role == "Admin")
        ).all()

    @classmethod
    def get_users_by_role(cls, db_session, role: str):
        """Get all users with a specific role."""
        return db_session.query(cls).filter(cls.role == role).all()

    @classmethod
    def get_viewer_users(cls, db_session):
        """Get all viewer users."""
        return db_session.query(cls).filter(cls.role == "Viewer").all()
