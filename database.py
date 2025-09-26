"""Database initialization and management utilities."""

import uuid
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from models import (
    Base,
    engine,
    AsyncSessionLocal,
    User,
    Role,
    Permission,
    RBACAction,
    RolePermission,
    UserRole,
    init_db,
)
from security import security_utils


class DatabaseInitializer:
    """Database initialization and setup utilities."""

    def __init__(self):
        self.db = None

    async def __aenter__(self):
        self.db = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            await self.db.close()

    async def create_tables(self):
        """Create all database tables."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")

    async def drop_tables(self):
        """Drop all database tables."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ Database tables dropped successfully")

    async def create_default_permissions(self):
        """Create default permissions."""
        permissions_data = [
            # User management permissions
            {
                "resource": "users",
                "action": RBACAction.read,
                "description": "View users",
            },
            {
                "resource": "users",
                "action": RBACAction.write,
                "description": "Create and update users",
            },
            {
                "resource": "users",
                "action": RBACAction.delete,
                "description": "Delete users",
            },
            {
                "resource": "users",
                "action": RBACAction.manage,
                "description": "Manage all user operations",
            },
            # Document permissions
            {
                "resource": "documents",
                "action": RBACAction.read,
                "description": "View documents",
            },
            {
                "resource": "documents",
                "action": RBACAction.write,
                "description": "Upload and update documents",
            },
            {
                "resource": "documents",
                "action": RBACAction.delete,
                "description": "Delete documents",
            },
            {
                "resource": "documents",
                "action": RBACAction.manage,
                "description": "Manage all document operations",
            },
            # Analysis permissions
            {
                "resource": "analyses",
                "action": RBACAction.read,
                "description": "View analyses",
            },
            {
                "resource": "analyses",
                "action": RBACAction.write,
                "description": "Create and update analyses",
            },
            {
                "resource": "analyses",
                "action": RBACAction.delete,
                "description": "Delete analyses",
            },
            {
                "resource": "analyses",
                "action": RBACAction.manage,
                "description": "Manage all analysis operations",
            },
            # Role and permission management
            {
                "resource": "roles",
                "action": RBACAction.read,
                "description": "View roles",
            },
            {
                "resource": "roles",
                "action": RBACAction.write,
                "description": "Create and update roles",
            },
            {
                "resource": "roles",
                "action": RBACAction.delete,
                "description": "Delete roles",
            },
            {
                "resource": "roles",
                "action": RBACAction.manage,
                "description": "Manage all role operations",
            },
            # System administration
            {
                "resource": "system",
                "action": RBACAction.read,
                "description": "View system information",
            },
            {
                "resource": "system",
                "action": RBACAction.manage,
                "description": "Manage system settings",
            },
            # Audit logs
            {
                "resource": "audit_logs",
                "action": RBACAction.read,
                "description": "View audit logs",
            },
        ]

        for perm_data in permissions_data:
            # Check if permission already exists
            existing_query = select(Permission).where(
                Permission.resource == perm_data["resource"],
                Permission.action == perm_data["action"],
            )
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue

            permission = Permission(
                resource=perm_data["resource"],
                action=perm_data["action"],
                description=perm_data["description"],
            )
            self.db.add(permission)

        await self.db.commit()
        print("✅ Default permissions created successfully")

    async def create_default_roles(self):
        """Create default roles with permissions."""
        roles_data = [
            {
                "name": "admin",
                "description": "System administrator with full access",
                "is_system_role": True,
                "permissions": [
                    # All permissions
                    ("users", RBACAction.manage),
                    ("documents", RBACAction.manage),
                    ("analyses", RBACAction.manage),
                    ("roles", RBACAction.manage),
                    ("system", RBACAction.manage),
                    ("audit_logs", RBACAction.read),
                ],
            },
            {
                "name": "analyst",
                "description": "Financial analyst with document and analysis access",
                "is_system_role": True,
                "permissions": [
                    # Document and analysis permissions
                    ("documents", RBACAction.read),
                    ("documents", RBACAction.write),
                    ("documents", RBACAction.delete),
                    ("analyses", RBACAction.read),
                    ("analyses", RBACAction.write),
                    ("analyses", RBACAction.delete),
                    # Limited user permissions (own profile)
                    ("users", RBACAction.read),
                ],
            },
            {
                "name": "viewer",
                "description": "Basic user with read-only access",
                "is_system_role": True,
                "permissions": [
                    # Read-only permissions
                    ("documents", RBACAction.read),
                    ("analyses", RBACAction.read),
                    ("users", RBACAction.read),
                ],
            },
        ]

        for role_data in roles_data:
            # Check if role already exists
            existing_query = select(Role).where(Role.name == role_data["name"])
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue

            # Create role
            role = Role(
                name=role_data["name"],
                description=role_data["description"],
                is_system_role=role_data["is_system_role"],
            )
            self.db.add(role)
            await self.db.flush()  # Get the role ID

            # Assign permissions
            for resource, action in role_data["permissions"]:
                permission_query = select(Permission).where(
                    Permission.resource == resource, Permission.action == action
                )
                permission_result = await self.db.execute(permission_query)
                permission = permission_result.scalar_one_or_none()

                if permission:
                    role_permission = RolePermission(
                        role_id=role.id, permission_id=permission.id
                    )
                    self.db.add(role_permission)

        await self.db.commit()
        print("✅ Default roles created successfully")

    async def create_admin_user(
        self,
        username: str = "admin",
        email: str = "admin@example.com",
        password: str = "Admin123!",
    ):
        """Create default admin user."""
        # Check if admin user already exists
        existing_query = select(User).where(User.username == username)
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            print(f"⚠️  Admin user '{username}' already exists")
            return

        # Create admin user
        hashed_password = security_utils.hash_password(password)
        admin_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            first_name="System",
            last_name="Administrator",
            is_active=True,
            is_verified=True,
        )
        self.db.add(admin_user)
        await self.db.flush()  # Get the user ID

        # Assign admin role
        admin_role_query = select(Role).where(Role.name == "admin")
        admin_role_result = await self.db.execute(admin_role_query)
        admin_role = admin_role_result.scalar_one_or_none()

        if admin_role:
            user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
            self.db.add(user_role)

        await self.db.commit()
        print(f"✅ Admin user '{username}' created successfully")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print("   ⚠️  Please change the default password after first login!")

    async def initialize_database(self, create_admin: bool = True):
        """Initialize the entire database with default data."""
        print("🚀 Initializing database...")

        # Create tables
        await self.create_tables()

        # Create default permissions
        await self.create_default_permissions()

        # Create default roles
        await self.create_default_roles()

        # Create admin user if requested
        if create_admin:
            await self.create_admin_user()

        print("✅ Database initialization completed successfully!")


async def init_database():
    """Initialize database with default data."""
    async with DatabaseInitializer() as initializer:
        await initializer.initialize_database()


async def reset_database():
    """Reset database (drop and recreate all tables)."""
    async with DatabaseInitializer() as initializer:
        await initializer.drop_tables()
        await initializer.initialize_database()


async def create_admin_user(
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "Admin123!",
):
    """Create admin user."""
    async with DatabaseInitializer() as initializer:
        await initializer.create_admin_user(username, email, password)


# Database health check
async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and health."""
    try:
        async with AsyncSessionLocal() as db:
            # Test basic connectivity
            result = await db.execute(text("SELECT 1"))
            result.scalar()

            # Check table existence
            tables_query = text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            )
            tables_result = await db.execute(tables_query)
            tables = [row[0] for row in tables_result.fetchall()]

            # Check user count
            user_count_query = select(User)
            user_count_result = await db.execute(user_count_query)
            user_count = len(user_count_result.scalars().all())

            return {
                "status": "healthy",
                "tables": tables,
                "user_count": user_count,
                "connection": "successful",
            }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "connection": "failed"}


if __name__ == "__main__":
    import asyncio

    async def main():
        """Main function for database initialization."""
        import sys

        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "init":
                await init_database()
            elif command == "reset":
                await reset_database()
            elif command == "admin":
                username = sys.argv[2] if len(sys.argv) > 2 else "admin"
                email = sys.argv[3] if len(sys.argv) > 3 else "admin@example.com"
                password = sys.argv[4] if len(sys.argv) > 4 else "Admin123!"
                await create_admin_user(username, email, password)
            elif command == "health":
                health = await check_database_health()
                print(f"Database Health: {health}")
            else:
                print("Available commands: init, reset, admin, health")
        else:
            await init_database()

    asyncio.run(main())
