"""
Script to run Alembic migrations.
Useful for CI/CD and deployment automation.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config
from src.database.connection import db_manager
from src.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def check_database_connection():
    """Check if database is accessible."""
    logger.info("Checking database connection...")

    try:
        db_manager.initialize_async_engine()
        is_healthy = await db_manager.check_connection()

        if not is_healthy:
            logger.error("Database connection check failed")
            return False

        logger.info("Database connection successful")
        await db_manager.close_async_engine()
        return True

    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        return False


def run_migrations(command_type="upgrade"):
    """
    Run Alembic migrations.

    Args:
        command_type: "upgrade", "downgrade", or "current"
    """
    logger.info(f"Running Alembic {command_type}...")

    # Load Alembic config
    alembic_cfg = Config("alembic.ini")

    try:
        if command_type == "upgrade":
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations applied successfully")

        elif command_type == "downgrade":
            command.downgrade(alembic_cfg, "-1")
            logger.info("Downgrade completed")

        elif command_type == "current":
            command.current(alembic_cfg)

        elif command_type == "history":
            command.history(alembic_cfg)

        else:
            logger.error(f"Unknown command: {command_type}")
            return False

        return True

    except Exception as e:
        logger.error(f"Migration {command_type} failed", error=str(e))
        return False


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Tech Spec Agent - Database Migration Tool")
    print("=" * 60)
    print()

    # Check database connection
    if not await check_database_connection():
        print("❌ Database connection failed. Please check:")
        print("  1. DATABASE_URL environment variable is set")
        print("  2. PostgreSQL is running")
        print("  3. Database credentials are correct")
        sys.exit(1)

    print("✅ Database connection successful")
    print()

    # Get command from args or default to upgrade
    command_type = sys.argv[1] if len(sys.argv) > 1 else "upgrade"

    print(f"Running: alembic {command_type}")
    print("-" * 60)

    # Run migrations
    success = run_migrations(command_type)

    if success:
        print()
        print("=" * 60)
        print("✅ Migration completed successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Migration failed")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
