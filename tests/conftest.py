"""
Pytest configuration and fixtures for Tech Spec Agent tests.
"""

# Load test environment variables BEFORE any other imports
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test file
env_path = Path(__file__).parent.parent / ".env.test"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    # Fallback: set minimal required env vars for tests
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
    os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://test:test@localhost/test")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy")
    os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
    os.environ.setdefault("TAVILY_API_KEY", "tvly-test-dummy")
    os.environ.setdefault("ANYON_API_BASE_URL", "http://localhost:3000")
    os.environ.setdefault("ANYON_WEBHOOK_SECRET", "test-secret")
    os.environ.setdefault("ANYON_FRONTEND_URL", "http://localhost:3000")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
    os.environ.setdefault("ENABLE_CACHING", "false")
    os.environ.setdefault("PROMETHEUS_ENABLED", "false")

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.database.connection import db_manager


# ============= Pytest Configuration =============

# Note: event_loop fixture removed to avoid conflicts with pytest-asyncio
# pytest-asyncio will automatically provide the event loop


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_db_manager():
    """
    Initialize db_manager for all tests that need it.
    This fixture runs automatically before any test session.
    """
    try:
        # Initialize the async engine
        db_manager.initialize_async_engine()
        yield
        # Cleanup after all tests
        await db_manager.close_async_engine()
    except Exception:
        # If initialization fails (e.g., no database available), skip tests that need it
        yield


# ============= Database Fixtures =============

@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide async database session for tests.
    Creates a fresh session for each test function.
    """
    # Use test database if configured
    database_url = settings.test_database_url or settings.database_url

    # Create engine for tests
    engine = create_async_engine(
        database_url,
        echo=settings.debug,
    )

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session
    async with async_session_maker() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
def sync_session() -> Generator[Session, None, None]:
    """
    Provide sync database session for tests.
    """
    database_url = settings.database_url_sync

    engine = create_engine(database_url, echo=settings.debug)
    session_maker = sessionmaker(engine, class_=Session)

    session = session_maker()
    yield session

    session.close()
    engine.dispose()


# ============= Sample Data Fixtures =============

@pytest.fixture
def sample_prd() -> str:
    """Sample PRD document for testing."""
    return """
    # Product Requirements Document

    ## Project Overview
    Building a modern SaaS application for project management.

    ## Features
    1. User Authentication (Email/Password, Google OAuth)
    2. Project Management (CRUD operations)
    3. Task Management with assignments
    4. File Upload and Storage
    5. Real-time Collaboration

    ## Technical Requirements
    - Must support 10,000+ concurrent users
    - Must be mobile-responsive
    - Must have role-based access control (Admin, Manager, Member)
    - Must integrate with Stripe for payments
    - Must send email notifications

    ## Non-Functional Requirements
    - Page load time < 2 seconds
    - 99.9% uptime SLA
    - GDPR compliant
    - SOC 2 Type II certified
    """


@pytest.fixture
def sample_design_docs() -> dict:
    """Sample design documents from Design Agent."""
    return {
        "design_system": "# Design System\n\nColors: Primary #667eea, Secondary #764ba2...",
        "ux_flow": "# UX Flow\n\n1. User logs in\n2. Dashboard displays...",
        "screen_specs": "# Screen Specifications\n\n## Login Screen\n- Email input\n- Password input..."
    }


@pytest.fixture
def sample_tech_gaps() -> list:
    """Sample identified technology gaps."""
    return [
        {
            "category": "authentication",
            "description": "User authentication system needed",
            "priority": "high",
            "required": True
        },
        {
            "category": "database",
            "description": "Database for storing user and project data",
            "priority": "critical",
            "required": True
        },
        {
            "category": "file_upload",
            "description": "File storage and upload handling",
            "priority": "high",
            "required": True
        },
        {
            "category": "email",
            "description": "Email notification service",
            "priority": "medium",
            "required": True
        },
        {
            "category": "payments",
            "description": "Payment processing integration",
            "priority": "high",
            "required": True
        },
    ]


@pytest.fixture
def sample_technology_options() -> dict:
    """Sample technology research results."""
    return {
        "authentication": [
            {
                "id": 1,
                "name": "NextAuth.js",
                "description": "Authentication library for Next.js applications",
                "pros": ["Easy setup", "Built-in providers", "Type-safe"],
                "cons": ["Tied to Next.js", "Limited customization"],
                "popularity": "High",
                "recommendation": True
            },
            {
                "id": 2,
                "name": "Passport.js",
                "description": "Flexible authentication middleware for Node.js",
                "pros": ["Framework agnostic", "Many strategies", "Mature"],
                "cons": ["Complex setup", "Callback-based"],
                "popularity": "High",
                "recommendation": False
            }
        ],
        "database": [
            {
                "id": 1,
                "name": "PostgreSQL",
                "description": "Advanced open-source relational database",
                "pros": ["ACID compliant", "Advanced features", "Highly scalable"],
                "cons": ["More complex than MySQL", "Heavier resource usage"],
                "popularity": "Very High",
                "recommendation": True
            },
            {
                "id": 2,
                "name": "MongoDB",
                "description": "Document-oriented NoSQL database",
                "pros": ["Flexible schema", "Easy to scale", "Fast for reads"],
                "cons": ["No joins", "Data duplication", "Complex transactions"],
                "popularity": "High",
                "recommendation": False
            }
        ]
    }


@pytest.fixture
def sample_ai_studio_code() -> str:
    """Sample TypeScript code from Google AI Studio."""
    return """
    // User authentication component
    import { useState } from 'react';
    import { useRouter } from 'next/navigation';

    export function LoginForm() {
        const [email, setEmail] = useState('');
        const [password, setPassword] = useState('');
        const router = useRouter();

        const handleSubmit = async (e) => {
            e.preventDefault();
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                router.push('/dashboard');
            }
        };

        return (
            <form onSubmit={handleSubmit}>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="submit">Login</button>
            </form>
        );
    }

    // API endpoint
    // POST /api/auth/login
    // Request: { email: string, password: string }
    // Response: { token: string, user: { id: string, email: string } }
    """


@pytest.fixture
def sample_trd() -> str:
    """Sample generated TRD document."""
    return """
    # Technical Requirements Document (TRD)

    ## 1. System Architecture
    - Frontend: Next.js 14 with TypeScript
    - Backend: NestJS (Node.js framework)
    - Database: PostgreSQL 15
    - Cache: Redis
    - Storage: AWS S3
    - Hosting: Vercel (Frontend), AWS ECS (Backend)

    ## 2. Authentication
    - Technology: NextAuth.js
    - Providers: Email/Password, Google OAuth
    - Session: JWT tokens (1-hour expiration)

    ## 3. Database Schema
    - Users table (id, email, password_hash, created_at)
    - Projects table (id, user_id, name, description, created_at)
    - Tasks table (id, project_id, title, status, assignee_id, due_date)

    ## 4. API Specifications
    - RESTful API with OpenAPI 3.0 specification
    - Authentication: Bearer token
    - Rate limiting: 100 requests/minute per user

    ## 5. Non-Functional Requirements
    - Performance: < 2 second page load
    - Scalability: 10,000+ concurrent users
    - Availability: 99.9% uptime
    - Security: OWASP Top 10 compliance
    """


# ============= Mock Services =============

@pytest.fixture
def mock_anthropic_api(monkeypatch):
    """Mock Anthropic API responses."""
    class MockAnthropicClient:
        async def ainvoke(self, *args, **kwargs):
            return "Mock TRD content generated by Claude"

    monkeypatch.setattr("langchain_anthropic.ChatAnthropic", MockAnthropicClient)
    return MockAnthropicClient()


@pytest.fixture
def mock_web_search(monkeypatch):
    """Mock web search API responses."""
    async def mock_search(*args, **kwargs):
        return [
            {"title": "NextAuth.js Documentation", "url": "https://next-auth.js.org", "snippet": "..."},
            {"title": "Passport.js Guide", "url": "https://passportjs.org", "snippet": "..."}
        ]

    monkeypatch.setattr("tavily.search", mock_search)
    return mock_search
