"""Setup script for Financial Document Analyzer."""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_database, create_admin_user, check_database_health


async def setup_database():
    """Setup database with initial data."""
    print("🚀 Setting up Financial Document Analyzer Database...")

    # Check if .env file exists
    if not os.path.exists(".env"):
        print(
            "⚠️  .env file not found. Please copy env.example to .env and configure it."
        )
        print("   cp env.example .env")
        return False

    try:
        # Initialize database
        await init_database()
        print("✅ Database setup completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False


async def create_admin():
    """Create admin user."""
    print("👤 Creating admin user...")

    try:
        username = input("Enter admin username (default: admin): ").strip() or "admin"
        email = (
            input("Enter admin email (default: admin@example.com): ").strip()
            or "admin@example.com"
        )
        password = (
            input("Enter admin password (default: Admin123!): ").strip() or "Admin123!"
        )

        await create_admin_user(username, email, password)
        print("✅ Admin user created successfully!")
        return True
    except Exception as e:
        print(f"❌ Admin user creation failed: {str(e)}")
        return False


async def check_health():
    """Check database health."""
    print("🔍 Checking database health...")

    try:
        health = await check_database_health()
        if health["status"] == "healthy":
            print("✅ Database is healthy!")
            print(f"   Tables: {len(health.get('tables', []))}")
            print(f"   Users: {health.get('user_count', 0)}")
        else:
            print("❌ Database is unhealthy!")
            print(f"   Error: {health.get('error', 'Unknown error')}")
        return health["status"] == "healthy"
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


async def main():
    """Main setup function."""
    if len(sys.argv) < 2:
        print("Usage: python setup.py <command>")
        print("Commands:")
        print("  init     - Initialize database with default data")
        print("  admin    - Create admin user")
        print("  health   - Check database health")
        print("  full     - Run full setup (init + admin)")
        return

    command = sys.argv[1].lower()

    if command == "init":
        await setup_database()
    elif command == "admin":
        await create_admin()
    elif command == "health":
        await check_health()
    elif command == "full":
        if await setup_database():
            await create_admin()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: init, admin, health, full")


if __name__ == "__main__":
    asyncio.run(main())
