"""
Integration tests for architecture generation workflow.

Tests the complete architecture generation pipeline:
- Database ERD generation
- System architecture diagram generation
- Architecture validation

These tests use mocked LLM responses for consistency.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from src.langgraph.nodes.generation_nodes import (
    generate_db_erd_node,
    generate_architecture_node,
    validate_architecture_node
)
from src.langgraph.state import TechSpecState


# ============= Mock LLM Response Fixtures =============

@pytest.fixture
def mock_database_schema():
    """Sample database schema for ERD generation."""
    return """
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE comments (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
def mock_erd_response():
    """Mock Mermaid ERD diagram response from LLM."""
    return """```mermaid
erDiagram
    USERS ||--o{ TASKS : creates
    USERS ||--o{ COMMENTS : writes
    TASKS ||--o{ COMMENTS : has

    USERS {
        uuid id PK
        string email
        string password_hash
        timestamp created_at
    }

    TASKS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string status
        timestamp due_date
        timestamp created_at
    }

    COMMENTS {
        uuid id PK
        uuid user_id FK
        uuid task_id FK
        text content
        timestamp created_at
    }
```"""


@pytest.fixture
def mock_architecture_response():
    """Mock system architecture diagram response from LLM."""
    return """```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        WebApp["Next.js Web Application"]
        MobileApp["React Native Mobile App"]
    end

    subgraph Gateway["API Gateway"]
        NGINX["NGINX Load Balancer<br/>(SSL, Rate Limiting)"]
    end

    subgraph Application["Application Layer"]
        API1["NestJS API Server 1<br/>(Port 3001)"]
        API2["NestJS API Server 2<br/>(Port 3002)"]

        subgraph Services["Business Services"]
            AuthSvc["Authentication Service"]
            TaskSvc["Task Service"]
            NotifSvc["Notification Service"]
        end
    end

    subgraph DataLayer["Data Layer"]
        PostgresMain["PostgreSQL Primary<br/>(Read/Write)"]
        PostgresRep1["PostgreSQL Replica 1<br/>(Read Only)"]
        Redis["Redis Cache"]
    end

    subgraph External["External Services"]
        OAuth["Google OAuth 2.0"]
        S3["AWS S3"]
        SendGrid["SendGrid"]
    end

    subgraph Monitoring["Monitoring"]
        Prom["Prometheus"]
        Grafana["Grafana"]
        Sentry["Sentry"]
    end

    WebApp -->|HTTPS| NGINX
    MobileApp -->|HTTPS| NGINX
    NGINX -->|Round Robin| API1
    NGINX -->|Round Robin| API2
    API1 --> AuthSvc
    API2 --> TaskSvc
    AuthSvc -->|Write| PostgresMain
    TaskSvc -->|Read| PostgresRep1
    PostgresMain -.->|Replication| PostgresRep1
    AuthSvc --> Redis
    AuthSvc --> OAuth
    API1 --> Prom
    Prom --> Grafana

    classDef clientStyle fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    classDef gatewayStyle fill:#50C878,stroke:#2E7D4E,stroke-width:2px,color:#fff
    classDef apiStyle fill:#F39C12,stroke:#C87F0A,stroke-width:2px,color:#fff
    classDef dataStyle fill:#E74C3C,stroke:#A93226,stroke-width:2px,color:#fff

    class WebApp,MobileApp clientStyle
    class NGINX gatewayStyle
    class API1,API2 apiStyle
    class PostgresMain,PostgresRep1,Redis dataStyle
```"""


@pytest.fixture
def mock_validation_response():
    """Mock architecture validation response from LLM."""
    return {
        "total_score": 88,
        "completeness_score": 27,
        "consistency_score": 23,
        "best_practices_score": 22,
        "scalability_score": 13,
        "security_score": 3,
        "strengths": [
            "All 6 layers properly represented",
            "Load balancing with multiple API servers",
            "Database replication for read scaling"
        ],
        "weaknesses": [
            "Monitoring layer could be more detailed",
            "External services could specify protocols"
        ],
        "recommendations": [
            "Add health check endpoints",
            "Show circuit breaker pattern for external services"
        ],
        "pass": True
    }


@pytest.fixture
def sample_state(mock_database_schema):
    """Sample TechSpecState for testing."""
    return {
        "session_id": str(uuid4()),
        "project_id": str(uuid4()),
        "user_id": str(uuid4()),
        "prd_content": "Build a task management application with user authentication and real-time updates",
        "design_docs": {
            "design_system": "Material Design UI components",
            "ux_flow": "Login → Dashboard → Task List → Task Detail"
        },
        "trd_draft": """# Technical Requirements Document

## 1. Project Overview
Task Management Application - A collaborative task management platform

## 2. Technology Stack
- Frontend: Next.js 14.2.3
- Backend: NestJS 10.3.2
- Database: PostgreSQL 14.11
- Cache: Redis 7.2
- Authentication: NextAuth.js 4.24.7

## 3. System Architecture
3-tier architecture with load balancing, database replication, and caching layer.
""",
        "database_schema": mock_database_schema,
        "user_decisions": [
            {"category": "frontend", "technology_name": "Next.js"},
            {"category": "backend", "technology_name": "NestJS"},
            {"category": "database", "technology_name": "PostgreSQL"},
            {"category": "caching", "technology_name": "Redis"},
            {"category": "authentication", "technology_name": "NextAuth.js"}
        ],
        "conversation_history": [],
        "errors": [],
        "iteration_count": 0,
        "current_stage": "db_schema_generated",
        "progress_percentage": 85.0,
        "updated_at": datetime.now().isoformat()
    }


# ============= Test: Database ERD Generation =============

@pytest.mark.asyncio
async def test_generate_db_erd_success(sample_state, mock_erd_response):
    """Test successful database ERD generation."""

    # Mock LLM client
    mock_response = MagicMock()
    mock_response.content = mock_erd_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        # Execute node
        result = await generate_db_erd_node(sample_state)

        # Assertions
        assert "database_erd" in result
        assert result["database_erd"] is not None
        assert "erDiagram" in result["database_erd"]
        assert "USERS" in result["database_erd"]
        assert "TASKS" in result["database_erd"]
        assert "COMMENTS" in result["database_erd"]
        assert "||--o{" in result["database_erd"]  # Relationship notation
        assert result["progress_percentage"] == 85.0
        assert result["current_stage"] == "generate_db_erd"

        # Verify conversation history updated
        assert len(result["conversation_history"]) > 0
        last_message = result["conversation_history"][-1]
        assert last_message["role"] == "agent"
        assert "ERD generated" in last_message["message"]


@pytest.mark.asyncio
async def test_generate_db_erd_no_schema(sample_state):
    """Test ERD generation when no database schema exists."""

    # Remove database schema
    sample_state["database_schema"] = ""

    # Execute node
    result = await generate_db_erd_node(sample_state)

    # Assertions
    assert "database_erd" in result
    assert "No schema available" in result["database_erd"]
    assert result["progress_percentage"] == 85.0


@pytest.mark.asyncio
async def test_generate_db_erd_llm_error(sample_state):
    """Test ERD generation when LLM fails."""

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(side_effect=Exception("LLM API error"))

        # Execute node
        result = await generate_db_erd_node(sample_state)

        # Assertions
        assert "database_erd" in result
        assert "ERD generation failed" in result["database_erd"]
        assert len(result["errors"]) > 0
        assert result["errors"][-1]["node"] == "generate_db_erd"


# ============= Test: System Architecture Generation =============

@pytest.mark.asyncio
async def test_generate_architecture_success(sample_state, mock_architecture_response):
    """Test successful system architecture generation."""

    mock_response = MagicMock()
    mock_response.content = mock_architecture_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        # Execute node
        result = await generate_architecture_node(sample_state)

        # Assertions
        assert "architecture_diagram" in result
        assert result["architecture_diagram"] is not None
        assert "flowchart TB" in result["architecture_diagram"]
        assert "Client Layer" in result["architecture_diagram"]
        assert "API Gateway" in result["architecture_diagram"]
        assert "Data Layer" in result["architecture_diagram"]
        assert "PostgreSQL Primary" in result["architecture_diagram"]
        assert "Redis Cache" in result["architecture_diagram"]
        assert result["progress_percentage"] == 90.0
        assert result["current_stage"] == "generate_architecture"

        # Verify conversation history
        assert len(result["conversation_history"]) > 0
        last_message = result["conversation_history"][-1]
        assert "architecture diagram generated" in last_message["message"]


@pytest.mark.asyncio
async def test_generate_architecture_with_technology_extraction(sample_state, mock_architecture_response):
    """Test that architecture generation extracts technologies correctly."""

    mock_response = MagicMock()
    mock_response.content = mock_architecture_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        # Add more specific technology decisions
        sample_state["user_decisions"] = [
            {"category": "database", "technology_name": "MongoDB"},
            {"category": "caching", "technology_name": "Memcached"},
            {"category": "authentication", "technology_name": "Passport.js"}
        ]

        # Execute node
        result = await generate_architecture_node(sample_state)

        # Verify LLM was called with correct prompt including technologies
        mock_llm_instance.generate.assert_called_once()
        call_args = mock_llm_instance.generate.call_args
        prompt = call_args[1]["messages"][0].content

        assert "MongoDB" in prompt
        assert "Memcached" in prompt
        assert "Passport.js" in prompt


@pytest.mark.asyncio
async def test_generate_architecture_llm_failure_uses_fallback(sample_state):
    """Test that fallback template is used when LLM fails."""

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(side_effect=Exception("LLM timeout"))

        # Execute node
        result = await generate_architecture_node(sample_state)

        # Assertions - should have fallback diagram
        assert "architecture_diagram" in result
        assert "flowchart TB" in result["architecture_diagram"]
        assert "Load Balancer" in result["architecture_diagram"]
        assert len(result["errors"]) > 0
        assert result["errors"][-1]["node"] == "generate_architecture"


@pytest.mark.asyncio
async def test_generate_architecture_empty_response_uses_fallback(sample_state):
    """Test that fallback is used when LLM returns empty response."""

    mock_response = MagicMock()
    mock_response.content = ""  # Empty response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        # Execute node
        result = await generate_architecture_node(sample_state)

        # Should use fallback
        assert "architecture_diagram" in result
        assert len(result["architecture_diagram"]) > 100
        assert "flowchart TB" in result["architecture_diagram"]


# ============= Test: Architecture Validation =============

@pytest.mark.asyncio
async def test_validate_architecture_success(sample_state, mock_architecture_response, mock_validation_response):
    """Test successful architecture validation."""

    # Add architecture diagram to state
    sample_state["architecture_diagram"] = mock_architecture_response.replace("```mermaid", "").replace("```", "")

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate_json = AsyncMock(return_value=mock_validation_response)

        # Execute node
        result = await validate_architecture_node(sample_state)

        # Assertions
        assert "architecture_validation" in result
        assert result["architecture_validation"]["total_score"] == 88
        assert result["architecture_validation"]["pass"] is True
        assert "validation_report" in result
        assert result["validation_report"]["architecture_score"] == 88
        assert result["progress_percentage"] == 92.0
        assert result["current_stage"] == "validate_architecture"

        # Verify conversation history
        assert len(result["conversation_history"]) > 0
        last_message = result["conversation_history"][-1]
        assert "Architecture Quality Score: 88/100" in last_message["message"]
        assert "✅ VALIDATED" in last_message["message"]


@pytest.mark.asyncio
async def test_validate_architecture_failing_score(sample_state, mock_architecture_response):
    """Test architecture validation with failing score."""

    sample_state["architecture_diagram"] = mock_architecture_response.replace("```mermaid", "").replace("```", "")

    # Mock response with low score
    low_score_response = {
        "total_score": 65,
        "completeness_score": 15,
        "consistency_score": 18,
        "best_practices_score": 17,
        "scalability_score": 10,
        "security_score": 5,
        "strengths": ["Basic architecture present"],
        "weaknesses": [
            "Missing monitoring layer",
            "No load balancing",
            "Single database instance"
        ],
        "recommendations": [
            "Add load balancer",
            "Implement database replication",
            "Add monitoring tools"
        ],
        "pass": False
    }

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate_json = AsyncMock(return_value=low_score_response)

        # Execute node
        result = await validate_architecture_node(sample_state)

        # Assertions
        assert result["architecture_validation"]["total_score"] == 65
        assert result["architecture_validation"]["pass"] is False

        # Verify warning message in conversation
        last_message = result["conversation_history"][-1]
        assert "⚠️ NEEDS REVIEW" in last_message["message"]


@pytest.mark.asyncio
async def test_validate_architecture_no_diagram(sample_state):
    """Test validation when no architecture diagram exists."""

    # No architecture diagram in state
    sample_state["architecture_diagram"] = ""

    # Execute node
    result = await validate_architecture_node(sample_state)

    # Assertions
    assert "architecture_validation" in result
    assert result["architecture_validation"]["total_score"] == 50
    assert result["architecture_validation"]["pass"] is False
    assert "No architecture diagram generated" in result["architecture_validation"]["message"]


@pytest.mark.asyncio
async def test_validate_architecture_llm_error(sample_state, mock_architecture_response):
    """Test validation when LLM fails - should assume pass."""

    sample_state["architecture_diagram"] = mock_architecture_response.replace("```mermaid", "").replace("```", "")

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate_json = AsyncMock(side_effect=Exception("LLM API error"))

        # Execute node
        result = await validate_architecture_node(sample_state)

        # Assertions - should default to passing
        assert "architecture_validation" in result
        assert result["architecture_validation"]["total_score"] == 75
        assert result["architecture_validation"]["pass"] is True
        assert "Could not validate automatically" in result["architecture_validation"]["weaknesses"]
        assert len(result["errors"]) > 0


# ============= Test: Complete Architecture Flow =============

@pytest.mark.asyncio
async def test_complete_architecture_generation_flow(
    sample_state,
    mock_erd_response,
    mock_architecture_response,
    mock_validation_response
):
    """Test complete architecture generation flow from ERD to validation."""

    # Mock all LLM calls
    mock_erd = MagicMock()
    mock_erd.content = mock_erd_response

    mock_arch = MagicMock()
    mock_arch.content = mock_architecture_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value

        # Step 1: Generate ERD
        mock_llm_instance.generate = AsyncMock(return_value=mock_erd)
        state_after_erd = await generate_db_erd_node(sample_state)

        assert "database_erd" in state_after_erd
        assert state_after_erd["progress_percentage"] == 85.0

        # Step 2: Generate Architecture
        mock_llm_instance.generate = AsyncMock(return_value=mock_arch)
        state_after_arch = await generate_architecture_node(state_after_erd)

        assert "architecture_diagram" in state_after_arch
        assert state_after_arch["progress_percentage"] == 90.0

        # Step 3: Validate Architecture
        mock_llm_instance.generate_json = AsyncMock(return_value=mock_validation_response)
        state_after_validation = await validate_architecture_node(state_after_arch)

        assert "architecture_validation" in state_after_validation
        assert state_after_validation["progress_percentage"] == 92.0
        assert state_after_validation["architecture_validation"]["pass"] is True

        # Verify final state has all architecture artifacts
        assert "database_erd" in state_after_validation
        assert "architecture_diagram" in state_after_validation
        assert "architecture_validation" in state_after_validation
        assert "validation_report" in state_after_validation
        assert state_after_validation["validation_report"]["architecture_score"] == 88


# ============= Test: Mermaid Syntax Validation =============

@pytest.mark.asyncio
async def test_erd_contains_valid_mermaid_syntax(sample_state, mock_erd_response):
    """Test that generated ERD contains valid Mermaid syntax."""

    mock_response = MagicMock()
    mock_response.content = mock_erd_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        result = await generate_db_erd_node(sample_state)

        erd = result["database_erd"]

        # Check for required Mermaid ERD syntax
        assert erd.startswith("erDiagram")
        assert "{" in erd and "}" in erd  # Table definitions
        assert "PK" in erd or "FK" in erd  # Key markers


@pytest.mark.asyncio
async def test_architecture_contains_valid_mermaid_syntax(sample_state, mock_architecture_response):
    """Test that generated architecture contains valid Mermaid flowchart syntax."""

    mock_response = MagicMock()
    mock_response.content = mock_architecture_response

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(return_value=mock_response)

        result = await generate_architecture_node(sample_state)

        arch = result["architecture_diagram"]

        # Check for required Mermaid flowchart syntax
        assert arch.startswith("flowchart TB") or arch.startswith("flowchart")
        assert "subgraph" in arch  # Layer grouping
        assert "-->" in arch or "-.->" in arch  # Arrows
        assert "[" in arch and "]" in arch  # Node definitions


# ============= Test: Error Recovery =============

@pytest.mark.asyncio
async def test_erd_generation_recovers_from_error(sample_state):
    """Test that ERD generation recovers gracefully from errors."""

    with patch('src.langgraph.nodes.generation_nodes.LLMClient') as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.generate = AsyncMock(side_effect=Exception("Network timeout"))

        result = await generate_db_erd_node(sample_state)

        # Should have fallback ERD
        assert "database_erd" in result
        assert "ERD generation failed" in result["database_erd"]

        # Should log error
        assert len(result["errors"]) > 0
        assert result["errors"][-1]["recoverable"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
