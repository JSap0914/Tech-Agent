"""
Database seeding script for Tech Spec Agent development environment.
Generates realistic test data for all tables.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, delete
from src.database.connection import db_manager
from src.database.models import (
    TechSpecSession,
    TechResearch,
    TechConversation,
    GeneratedTRDDocument,
    AgentErrorLog,
    DesignJob,
)
import structlog

logger = structlog.get_logger(__name__)


# ============= Sample Data Generators =============

def generate_sample_sessions(design_job_ids: List[str], count: int = 10) -> List[TechSpecSession]:
    """Generate sample Tech Spec sessions."""
    sessions = []
    statuses = ["pending", "in_progress", "paused", "completed", "failed"]
    stages = [
        "initializing",
        "loading_design_docs",
        "identifying_gaps",
        "researching_technologies",
        "awaiting_user_decision",
        "generating_trd",
        "validating_output",
        "completed",
    ]

    for i in range(count):
        created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        status = random.choice(statuses)

        # Completed sessions should have completed_at timestamp
        completed_at = None
        if status == "completed":
            completed_at = created_at + timedelta(minutes=random.randint(15, 60))

        session = TechSpecSession(
            id=uuid4(),
            project_id=uuid4(),
            design_job_id=random.choice(design_job_ids),
            user_id=uuid4(),
            status=status,
            current_stage=random.choice(stages),
            progress_percentage=random.uniform(0, 100) if status != "completed" else 100.0,
            session_data={
                "prd_loaded": True,
                "gaps_identified": random.randint(3, 8),
                "decisions_made": random.randint(0, 5),
                "current_category": random.choice(["authentication", "database", "storage", "email"]),
            },
            websocket_url=f"wss://anyon.com/tech-spec/{uuid4()}",
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=random.randint(5, 120)),
            completed_at=completed_at,
        )
        sessions.append(session)

    return sessions


def generate_sample_research(session_ids: List[str], count_per_session: int = 3) -> List[TechResearch]:
    """Generate sample technology research records."""
    research_records = []
    categories = [
        "authentication",
        "database",
        "file_upload",
        "email",
        "payments",
        "frontend_framework",
        "backend_framework",
        "caching",
        "real_time",
        "deployment",
    ]

    for session_id in session_ids:
        for _ in range(count_per_session):
            category = random.choice(categories)

            research = TechResearch(
                id=uuid4(),
                session_id=session_id,
                technology_category=category,
                gap_description=f"Need {category} solution for the application",
                researched_options=[
                    {
                        "name": f"Option A for {category}",
                        "description": f"Popular {category} solution",
                        "pros": ["Easy to use", "Well documented", "Large community"],
                        "cons": ["Limited customization", "Vendor lock-in"],
                        "popularity": "High",
                        "recommendation": True,
                    },
                    {
                        "name": f"Option B for {category}",
                        "description": f"Alternative {category} solution",
                        "pros": ["Flexible", "Open source", "Self-hosted"],
                        "cons": ["Complex setup", "Smaller community"],
                        "popularity": "Medium",
                        "recommendation": False,
                    },
                ],
                selected_technology=f"Option A for {category}" if random.random() > 0.3 else None,
                selection_reasoning=f"Best fit for {category} requirements",
                decision_timestamp=datetime.utcnow() - timedelta(minutes=random.randint(10, 300)),
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(30, 360)),
            )
            research_records.append(research)

    return research_records


def generate_sample_conversations(
    session_ids: List[str],
    research_ids: List[str],
    count_per_session: int = 5,
) -> List[TechConversation]:
    """Generate sample conversation records."""
    conversations = []

    for session_id in session_ids:
        # Select random research IDs for this session (some conversations may not be tied to research)
        relevant_research_ids = random.sample(research_ids, min(3, len(research_ids)))

        for i in range(count_per_session):
            role = random.choice(["user", "agent", "system"])
            message_types = {
                "user": ["decision_response", "clarification", "question"],
                "agent": ["option_presentation", "question", "confirmation"],
                "system": ["status_update", "error", "completion"],
            }

            messages = {
                "user": [
                    "I prefer NextAuth.js for authentication",
                    "Can you explain the pros and cons of PostgreSQL?",
                    "I want to use AWS S3 for file storage",
                    "What about pricing for these options?",
                ],
                "agent": [
                    "I've identified 5 technology gaps. Let's start with authentication.",
                    "For authentication, I recommend NextAuth.js or Passport.js. Which would you prefer?",
                    "Based on your requirements, PostgreSQL is the best choice for your database.",
                    "Great choice! I'll use NextAuth.js in the TRD.",
                ],
                "system": [
                    "Session initialized successfully",
                    "PRD and design documents loaded",
                    "Technology research completed for authentication",
                    "TRD generation completed with quality score 95%",
                ],
            }

            conversation = TechConversation(
                id=uuid4(),
                session_id=session_id,
                research_id=random.choice(relevant_research_ids) if relevant_research_ids and role != "system" else None,
                role=role,
                message=random.choice(messages[role]),
                message_type=random.choice(message_types[role]),
                metadata={
                    "client_info": "web_browser" if role == "user" else "agent",
                    "processing_time_ms": random.randint(100, 2000),
                },
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 180)),
            )
            conversations.append(conversation)

    return conversations


def generate_sample_trd_documents(session_ids: List[str], count: int = 5) -> List[GeneratedTRDDocument]:
    """Generate sample TRD documents."""
    documents = []

    for session_id in random.sample(session_ids, min(count, len(session_ids))):
        doc = GeneratedTRDDocument(
            id=uuid4(),
            session_id=session_id,
            trd_content="""# Technical Requirements Document (TRD)

## 1. System Architecture
- Frontend: Next.js 14 with TypeScript
- Backend: NestJS
- Database: PostgreSQL 15
- Authentication: NextAuth.js
- File Storage: AWS S3
- Email: SendGrid
- Payments: Stripe

## 2. Database Schema
[Full database schema with tables...]

## 3. API Specifications
[RESTful API endpoints with OpenAPI spec...]

## 4. Security Requirements
[Authentication, authorization, encryption...]

## 5. Performance Requirements
- Page load: < 2 seconds
- API response: < 200ms
- Concurrent users: 10,000+
""",
            api_specification='{"openapi": "3.0.0", "info": {"title": "Project API"}}',
            database_schema="CREATE TABLE users (id UUID PRIMARY KEY, email VARCHAR(255) UNIQUE);",
            architecture_diagram="graph TD\n  A[Frontend] --> B[API]\n  B --> C[Database]",
            tech_stack_document="# Tech Stack\n\n- **Frontend**: Next.js 14\n- **Backend**: NestJS",
            quality_score=random.uniform(85.0, 98.0),
            validation_report={
                "completeness": random.uniform(90, 100),
                "technical_accuracy": random.uniform(85, 100),
                "requirements_coverage": random.uniform(90, 100),
                "issues": [],
            },
            version=random.randint(1, 3),
            created_at=datetime.utcnow() - timedelta(minutes=random.randint(30, 1440)),
        )
        documents.append(doc)

    return documents


def generate_sample_error_logs(session_ids: List[str], count: int = 10) -> List[AgentErrorLog]:
    """Generate sample error logs."""
    error_logs = []
    nodes = [
        "load_design_outputs",
        "identify_gaps",
        "research_technologies",
        "present_options",
        "generate_trd",
        "validate_trd",
    ]
    error_types = ["api_error", "validation_error", "timeout", "llm_error", "database_error"]
    recovery_strategies = ["retry_with_backoff", "fallback_to_cache", "skip_optional_step", "manual_intervention"]

    for _ in range(count):
        error = AgentErrorLog(
            id=uuid4(),
            session_id=random.choice(session_ids),
            node=random.choice(nodes),
            error_type=random.choice(error_types),
            message=f"Error in {random.choice(nodes)}: {random.choice(['API rate limit', 'Timeout', 'Invalid response'])}",
            stack_trace="Traceback (most recent call last):\n  File ...\n  Error: ...",
            retry_count=random.randint(0, 3),
            recovered=random.choice([True, False]),
            recovery_strategy=random.choice(recovery_strategies) if random.random() > 0.3 else None,
            created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 1440)),
        )
        error_logs.append(error)

    return error_logs


# ============= Main Seeding Function =============

async def seed_database(clear_existing: bool = False):
    """
    Seed the database with sample data.

    Args:
        clear_existing: If True, delete all existing data first
    """
    logger.info("Starting database seeding...")

    # Initialize database connection
    db_manager.initialize_async_engine()

    try:
        async with db_manager.get_async_session() as session:
            # Clear existing data if requested
            if clear_existing:
                logger.info("Clearing existing data...")
                await session.execute(delete(AgentErrorLog))
                await session.execute(delete(GeneratedTRDDocument))
                await session.execute(delete(TechConversation))
                await session.execute(delete(TechResearch))
                await session.execute(delete(TechSpecSession))
                await session.commit()
                logger.info("Existing data cleared")

            # Generate design job IDs (simulating Design Agent data)
            # In production, these would exist in shared.design_jobs
            # We need to create stub DesignJob records to satisfy FK constraints
            design_job_ids = []
            logger.info("Creating stub Design Agent jobs for FK constraints...")

            try:
                # Attempt to create DesignJob records
                # This will fail if shared schema doesn't exist yet
                for i in range(5):
                    design_job = DesignJob(
                        id=uuid4(),
                        project_id=uuid4(),
                        status="completed",
                        created_at=datetime.utcnow(),
                    )
                    design_job_ids.append(str(design_job.id))
                    session.add(design_job)

                await session.commit()
                logger.info(f"Created {len(design_job_ids)} stub design jobs")

            except Exception as e:
                # If Design Agent schema doesn't exist, can't create sessions with FK
                logger.error(
                    "Cannot create Design Agent jobs. Shared schema may not exist.",
                    error=str(e)
                )
                logger.info(
                    "To seed Tech Spec data, ensure Design Agent shared schema exists first."
                )
                raise ValueError(
                    "Cannot seed database: shared.design_jobs table not accessible. "
                    "Run Design Agent migrations first or disable FK constraints."
                )

            # Generate sessions
            logger.info("Generating Tech Spec sessions...")
            sessions = generate_sample_sessions(design_job_ids, count=10)
            session_ids = [str(s.id) for s in sessions]

            for s in sessions:
                session.add(s)
            await session.commit()
            logger.info(f"Created {len(sessions)} sessions")

            # Generate research records
            logger.info("Generating technology research records...")
            research_records = generate_sample_research(session_ids, count_per_session=3)
            research_ids = [str(r.id) for r in research_records]

            for r in research_records:
                session.add(r)
            await session.commit()
            logger.info(f"Created {len(research_records)} research records")

            # Generate conversations
            logger.info("Generating conversation records...")
            conversations = generate_sample_conversations(session_ids, research_ids, count_per_session=8)

            for c in conversations:
                session.add(c)
            await session.commit()
            logger.info(f"Created {len(conversations)} conversations")

            # Generate TRD documents
            logger.info("Generating TRD documents...")
            trd_documents = generate_sample_trd_documents(session_ids, count=6)

            for doc in trd_documents:
                session.add(doc)
            await session.commit()
            logger.info(f"Created {len(trd_documents)} TRD documents")

            # Generate error logs
            logger.info("Generating error logs...")
            error_logs = generate_sample_error_logs(session_ids, count=15)

            for error in error_logs:
                session.add(error)
            await session.commit()
            logger.info(f"Created {len(error_logs)} error logs")

            logger.info("✅ Database seeding completed successfully!")
            logger.info(f"Summary:")
            logger.info(f"  - Sessions: {len(sessions)}")
            logger.info(f"  - Research records: {len(research_records)}")
            logger.info(f"  - Conversations: {len(conversations)}")
            logger.info(f"  - TRD documents: {len(trd_documents)}")
            logger.info(f"  - Error logs: {len(error_logs)}")

    except Exception as e:
        logger.error("Database seeding failed", error=str(e), exc_info=True)
        raise
    finally:
        await db_manager.close_async_engine()


# ============= CLI =============

async def main():
    """Main entry point."""
    print("=" * 60)
    print("Tech Spec Agent - Database Seeding Tool")
    print("=" * 60)
    print()

    # Check for --clear flag
    clear_existing = "--clear" in sys.argv or "-c" in sys.argv

    if clear_existing:
        print("⚠️  WARNING: This will delete all existing data!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    print("Starting database seeding...")
    print()

    try:
        await seed_database(clear_existing=clear_existing)
        print()
        print("=" * 60)
        print("✅ Seeding completed successfully")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Seeding failed: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
