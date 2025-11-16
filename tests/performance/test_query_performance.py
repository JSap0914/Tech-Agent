"""
Performance tests for database queries.
Tests query execution time and ensures they meet performance requirements.
"""

import pytest
import time
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload

from src.database.models import (
    TechSpecSession,
    TechResearch,
    TechConversation,
    GeneratedTRDDocument,
    AgentErrorLog,
    DesignJob,
)
from src.database.connection import db_manager


# ============= Performance Thresholds =============

# Maximum acceptable query times (in milliseconds)
QUERY_TIME_THRESHOLDS = {
    "session_by_id": 5,  # Single record lookup by primary key
    "session_list_by_status": 50,  # List with filtering and ordering
    "research_by_session": 20,  # Related records lookup
    "conversation_history": 30,  # Paginated history
    "cross_schema_join": 100,  # JOIN across schemas
    "aggregation_query": 50,  # COUNT, AVG, etc.
}


# ============= Helper Functions =============

def measure_query_time(func):
    """Decorator to measure query execution time."""

    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        return result, elapsed_ms

    return wrapper


# ============= Performance Tests =============


@pytest.mark.performance
@pytest.mark.asyncio
async def test_session_lookup_by_id_performance(stub_design_jobs):
    """Test that looking up a session by ID is fast (< 5ms)."""

    @measure_query_time
    async def query_session_by_id(session_id: str):
        async with db_manager.get_async_session() as session:
            query = select(TechSpecSession).where(TechSpecSession.id == session_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    # Create a test session with valid FK
    test_id = uuid4()
    async with db_manager.get_async_session() as session:
        test_session = TechSpecSession(
            id=test_id,
            project_id=uuid4(),
            design_job_id=stub_design_jobs[0],  # Use valid design_job_id
            status="pending",
            progress_percentage=0.0,
        )
        session.add(test_session)
        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_session_by_id(str(test_id))

    # Assertions
    assert result is not None
    assert elapsed_ms < QUERY_TIME_THRESHOLDS["session_by_id"], (
        f"Session lookup took {elapsed_ms:.2f}ms, "
        f"exceeds threshold of {QUERY_TIME_THRESHOLDS['session_by_id']}ms"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_session_list_by_status_performance(stub_design_jobs):
    """Test that listing sessions by status is fast (< 50ms)."""

    @measure_query_time
    async def query_sessions_by_status(status: str, limit: int = 50):
        async with db_manager.get_async_session() as session:
            query = (
                select(TechSpecSession)
                .where(TechSpecSession.status == status)
                .order_by(TechSpecSession.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            return result.scalars().all()

    # Create test sessions with various statuses
    async with db_manager.get_async_session() as session:
        for i in range(20):
            test_session = TechSpecSession(
                id=uuid4(),
                project_id=uuid4(),
                design_job_id=stub_design_jobs[i % len(stub_design_jobs)],  # Use valid FK
                status="in_progress" if i % 2 == 0 else "completed",
                progress_percentage=float(i * 5),
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            session.add(test_session)
        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_sessions_by_status("in_progress", limit=50)

    # Assertions
    assert len(result) > 0
    assert elapsed_ms < QUERY_TIME_THRESHOLDS["session_list_by_status"], (
        f"Session list query took {elapsed_ms:.2f}ms, "
        f"exceeds threshold of {QUERY_TIME_THRESHOLDS['session_list_by_status']}ms"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_research_by_session_performance(stub_design_jobs):
    """Test that loading research records for a session is fast (< 20ms)."""

    @measure_query_time
    async def query_research_by_session(session_id: str):
        async with db_manager.get_async_session() as session:
            query = select(TechResearch).where(TechResearch.session_id == session_id)
            result = await session.execute(query)
            return result.scalars().all()

    # Create test data
    test_session_id = uuid4()
    async with db_manager.get_async_session() as session:
        test_session = TechSpecSession(
            id=test_session_id,
            project_id=uuid4(),
            design_job_id=stub_design_jobs[0],  # Use valid FK
            status="in_progress",
            progress_percentage=50.0,
        )
        session.add(test_session)

        # Add multiple research records
        for i in range(5):
            research = TechResearch(
                id=uuid4(),
                session_id=test_session_id,
                technology_category=f"category_{i}",
                researched_options=[{"name": f"option_{i}", "score": 90 + i}],
            )
            session.add(research)

        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_research_by_session(str(test_session_id))

    # Assertions
    assert len(result) == 5
    assert elapsed_ms < QUERY_TIME_THRESHOLDS["research_by_session"], (
        f"Research lookup took {elapsed_ms:.2f}ms, "
        f"exceeds threshold of {QUERY_TIME_THRESHOLDS['research_by_session']}ms"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_conversation_history_performance(stub_design_jobs):
    """Test that loading paginated conversation history is fast (< 30ms)."""

    @measure_query_time
    async def query_conversation_history(session_id: str, limit: int = 50):
        async with db_manager.get_async_session() as session:
            query = (
                select(TechConversation)
                .where(TechConversation.session_id == session_id)
                .order_by(TechConversation.timestamp.asc())
                .limit(limit)
            )
            result = await session.execute(query)
            return result.scalars().all()

    # Create test data
    test_session_id = uuid4()
    async with db_manager.get_async_session() as session:
        test_session = TechSpecSession(
            id=test_session_id,
            project_id=uuid4(),
            design_job_id=stub_design_jobs[0],  # Use valid FK
            status="in_progress",
            progress_percentage=50.0,
        )
        session.add(test_session)

        # Add conversation history
        for i in range(100):
            conversation = TechConversation(
                id=uuid4(),
                session_id=test_session_id,
                role="user" if i % 2 == 0 else "agent",
                message=f"Message {i}",
                timestamp=datetime.utcnow() - timedelta(minutes=100 - i),
            )
            session.add(conversation)

        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_conversation_history(str(test_session_id), limit=50)

    # Assertions
    assert len(result) == 50
    assert elapsed_ms < QUERY_TIME_THRESHOLDS["conversation_history"], (
        f"Conversation history query took {elapsed_ms:.2f}ms, "
        f"exceeds threshold of {QUERY_TIME_THRESHOLDS['conversation_history']}ms"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_aggregation_query_performance(stub_design_jobs):
    """Test that aggregation queries are fast (< 50ms)."""

    @measure_query_time
    async def query_session_statistics():
        async with db_manager.get_async_session() as session:
            query = select(
                TechSpecSession.status,
                func.count(TechSpecSession.id).label("count"),
                func.avg(TechSpecSession.progress_percentage).label("avg_progress"),
            ).group_by(TechSpecSession.status)

            result = await session.execute(query)
            return result.all()

    # Create test data with various statuses
    async with db_manager.get_async_session() as session:
        statuses = ["pending", "in_progress", "completed", "failed"]
        for i in range(40):
            test_session = TechSpecSession(
                id=uuid4(),
                project_id=uuid4(),
                design_job_id=stub_design_jobs[i % len(stub_design_jobs)],  # Use valid FK
                status=statuses[i % len(statuses)],
                progress_percentage=float(i * 2.5),
            )
            session.add(test_session)
        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_session_statistics()

    # Assertions
    assert len(result) > 0
    assert elapsed_ms < QUERY_TIME_THRESHOLDS["aggregation_query"], (
        f"Aggregation query took {elapsed_ms:.2f}ms, "
        f"exceeds threshold of {QUERY_TIME_THRESHOLDS['aggregation_query']}ms"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_relationship_loading_performance(stub_design_jobs):
    """Test that loading related records via relationships is efficient."""

    @measure_query_time
    async def query_session_with_relationships(session_id: str):
        async with db_manager.get_async_session() as session:
            query = (
                select(TechSpecSession)
                .where(TechSpecSession.id == session_id)
                .options(
                    selectinload(TechSpecSession.tech_research),
                    selectinload(TechSpecSession.conversations),
                )
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    # Create test data with relationships
    test_session_id = uuid4()
    async with db_manager.get_async_session() as session:
        test_session = TechSpecSession(
            id=test_session_id,
            project_id=uuid4(),
            design_job_id=stub_design_jobs[0],  # Use valid FK
            status="in_progress",
            progress_percentage=50.0,
        )
        session.add(test_session)

        # Add related records
        for i in range(3):
            research = TechResearch(
                id=uuid4(),
                session_id=test_session_id,
                technology_category=f"category_{i}",
                researched_options=[{"name": f"option_{i}"}],
            )
            session.add(research)

        for i in range(10):
            conversation = TechConversation(
                id=uuid4(),
                session_id=test_session_id,
                role="user" if i % 2 == 0 else "agent",
                message=f"Message {i}",
            )
            session.add(conversation)

        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_session_with_relationships(str(test_session_id))

    # Assertions
    assert result is not None
    assert len(result.tech_research) == 3
    assert len(result.conversations) == 10

    # This should be fast due to selectinload (avoids N+1 problem)
    assert elapsed_ms < 100, f"Relationship loading took {elapsed_ms:.2f}ms, should use selectinload"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_error_log_query_performance():
    """Test that querying error logs by filters is fast."""

    @measure_query_time
    async def query_unrecovered_errors(limit: int = 50):
        async with db_manager.get_async_session() as session:
            query = (
                select(AgentErrorLog)
                .where(AgentErrorLog.recovered == False)
                .order_by(AgentErrorLog.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            return result.scalars().all()

    # Create test error logs
    async with db_manager.get_async_session() as session:
        test_session_id = uuid4()
        for i in range(50):
            error = AgentErrorLog(
                id=uuid4(),
                session_id=test_session_id,
                node=f"node_{i % 5}",
                error_type="api_error",
                message=f"Error {i}",
                retry_count=i % 3,
                recovered=i % 3 == 0,  # 1/3 recovered, 2/3 unrecovered
                created_at=datetime.utcnow() - timedelta(minutes=i),
            )
            session.add(error)
        await session.commit()

    # Measure query performance
    result, elapsed_ms = await query_unrecovered_errors(limit=50)

    # Assertions
    assert len(result) > 0
    assert all(not e.recovered for e in result)
    assert elapsed_ms < 50, f"Error log query took {elapsed_ms:.2f}ms"


# ============= Performance Summary =============


@pytest.mark.performance
@pytest.mark.asyncio
async def test_generate_performance_report(stub_design_jobs):
    """
    Generate a performance report for all queries.
    This test runs all performance-critical queries and reports timing.
    """
    results: List[Dict[str, Any]] = []

    # Test 1: Session by ID
    test_id = uuid4()
    async with db_manager.get_async_session() as session:
        test_session = TechSpecSession(
            id=test_id,
            project_id=uuid4(),
            design_job_id=stub_design_jobs[0],  # Use valid FK
            status="pending",
            progress_percentage=0.0,
        )
        session.add(test_session)
        await session.commit()

    start = time.perf_counter()
    async with db_manager.get_async_session() as session:
        query = select(TechSpecSession).where(TechSpecSession.id == test_id)
        await session.execute(query)
    elapsed = (time.perf_counter() - start) * 1000

    results.append(
        {
            "query": "Session by ID",
            "time_ms": round(elapsed, 2),
            "threshold_ms": QUERY_TIME_THRESHOLDS["session_by_id"],
            "status": "✅" if elapsed < QUERY_TIME_THRESHOLDS["session_by_id"] else "❌",
        }
    )

    # Print report
    print("\n" + "=" * 70)
    print("QUERY PERFORMANCE REPORT")
    print("=" * 70)
    print(f"{'Query':<30} {'Time (ms)':<12} {'Threshold':<12} {'Status':<6}")
    print("-" * 70)

    for r in results:
        print(f"{r['query']:<30} {r['time_ms']:<12} {r['threshold_ms']:<12} {r['status']:<6}")

    print("=" * 70)

    # All queries should pass
    assert all(r["status"] == "✅" for r in results), "Some queries exceeded performance thresholds"
