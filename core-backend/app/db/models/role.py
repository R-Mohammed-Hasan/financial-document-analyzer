"""
Role and UserRole database models.

This module defines the Role and UserRole SQLAlchemy models for role-based access control.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Table,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.base import Base

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "assigned_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    Column("assigned_by", Integer, ForeignKey("users.id"), nullable=True),
)


class Role(Base):
    """
    Role model for role-based access control.

    Attributes:
        id: Primary key
        name: Role name (unique)
        description: Role description
        permissions: JSON string of role permissions
        is_active: Whether the role is active
        created_at: Role creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string of permissions
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:
        """String representation of the role."""
        return f"<Role(id={self.id}, name={self.name})>"

    def to_dict(self) -> dict:
        """Convert role to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_count": len(self.users),
        }

    def activate(self) -> None:
        """Activate the role."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the role."""
        self.is_active = False

    def has_permission(self, permission: str) -> bool:
        """
        Check if role has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if role has permission, False otherwise
        """
        if not self.permissions:
            return False

        try:
            import json

            permissions_list = json.loads(self.permissions)
            return permission in permissions_list
        except (json.JSONDecodeError, TypeError):
            return False

    def add_permission(self, permission: str) -> None:
        """
        Add a permission to the role.

        Args:
            permission: Permission to add
        """
        try:
            import json

            permissions_list = json.loads(self.permissions) if self.permissions else []
            if permission not in permissions_list:
                permissions_list.append(permission)
                self.permissions = json.dumps(permissions_list)
        except (json.JSONDecodeError, TypeError):
            self.permissions = json.dumps([permission])

    def remove_permission(self, permission: str) -> None:
        """
        Remove a permission from the role.

        Args:
            permission: Permission to remove
        """
        try:
            import json

            permissions_list = json.loads(self.permissions) if self.permissions else []
            if permission in permissions_list:
                permissions_list.remove(permission)
                self.permissions = json.dumps(permissions_list)
        except (json.JSONDecodeError, TypeError):
            pass

    @classmethod
    def get_by_name(cls, name: str):
        """Get role by name."""
        return cls.query.filter(cls.name == name).first()

    @classmethod
    def get_active_roles(cls):
        """Get all active roles."""
        return cls.query.filter(cls.is_active == True).all()

    @classmethod
    def get_default_roles(cls):
        """Get default roles that are commonly used."""
        default_role_names = ["user", "admin", "moderator"]
        return cls.query.filter(cls.name.in_(default_role_names)).all()


class UserRole(Base):
    """
    UserRole model for tracking role assignments.

    Attributes:
        user_id: Foreign key to user
        role_id: Foreign key to role
        assigned_at: Assignment timestamp
        assigned_by: User who assigned the role
    """

    __tablename__ = "user_roles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("Role")
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        """String representation of the user role."""
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"

    def to_dict(self) -> dict:
        """Convert user role to dictionary."""
        return {
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role.name if self.role else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
        }

    @classmethod
    def get_user_roles(cls, user_id: int) -> List["UserRole"]:
        """Get all roles for a user."""
        return cls.query.filter(cls.user_id == user_id).all()

    @classmethod
    def get_role_users(cls, role_id: int) -> List["UserRole"]:
        """Get all users with a specific role."""
        return cls.query.filter(cls.role_id == role_id).all()

    @classmethod
    def assign_role(cls, user_id: int, role_id: int, assigned_by: Optional[int] = None):
        """Assign a role to a user."""
        user_role = cls(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        cls.session.add(user_role)
        cls.session.commit()
        return user_role

    @classmethod
    def revoke_role(cls, user_id: int, role_id: int):
        """Revoke a role from a user."""
        user_role = cls.query.filter(
            cls.user_id == user_id, cls.role_id == role_id
        ).first()

        if user_role:
            cls.session.delete(user_role)
            cls.session.commit()
            return True
        return False
