"""
Performance test fixtures.
Handles database initialization and cleanup for performance tests.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from src.database.connection import db_manager
from src.database.models import DesignJob


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_performance_db():
    """
    Initialize db_manager for performance tests.
    Runs once per test session.
    """
    # Initialize async engine
    db_manager.initialize_async_engine()

    yield

    # Cleanup
    await db_manager.close_async_engine()


@pytest_asyncio.fixture(scope="function")
async def stub_design_jobs():
    """
    Create stub Design Agent jobs for FK constraints in performance tests.
    Returns list of design_job_id UUIDs that can be used in tests.
    """
    design_job_ids = []

    try:
        async with db_manager.get_async_session() as session:
            # Create 5 stub design jobs
            for i in range(5):
                design_job = DesignJob(
                    id=uuid4(),
                    project_id=uuid4(),
                    status="completed",
                    created_at=datetime.utcnow(),
                )
                design_job_ids.append(design_job.id)
                session.add(design_job)

            await session.commit()

    except Exception as e:
        # If Design Agent tables don't exist, skip tests that need them
        pytest.skip(f"Design Agent tables not present: {e}")

    yield design_job_ids

    # Cleanup: delete stub jobs after test
    # (CASCADE will automatically delete related TechSpecSessions)
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import delete
            await session.execute(
                delete(DesignJob).where(DesignJob.id.in_(design_job_ids))
            )
            await session.commit()
    except Exception:
        # Cleanup failure is not critical
        pass
