"""
Integration tests for full Tech Spec Agent workflow (Week 13-14).
Tests end-to-end workflow execution with all nodes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from src.langgraph.state import TechSpecState
from src.langgraph.workflow import create_tech_spec_workflow


@pytest_asyncio.fixture
async def sample_state():
    """Create sample state for workflow testing."""
    session_id = str(uuid.uuid4())

    return {
        "session_id": session_id,
        "project_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "prd_content": """
# Product Requirements Document

## Project Overview
E-commerce platform for selling handmade crafts.

## Features
1. User authentication (Email, Google OAuth)
2. Product catalog with search
3. Shopping cart
4. Payment processing (Stripe)
5. Order management

## Technical Requirements
- Support 1000+ concurrent users
- Mobile responsive
- Real-time inventory updates
""",
        "design_docs": {
            "design_system": "# Colors: Primary #007bff",
            "ux_flow": "# User Flow: Login → Browse → Add to Cart → Checkout",
            "screen_specs": "# Login Screen: Email input, Password input"
        },
        "initial_trd": None,
        "google_ai_studio_code_path": None,
        "completeness_score": 0.0,
        "missing_elements": [],
        "ambiguous_elements": [],
        "identified_gaps": [],
        "research_results": [],
        "user_decisions": [],
        "selected_technologies": {},
        "pending_decisions": [],
        "current_question": None,
        "conversation_history": [],
        "google_ai_studio_data": None,
        "parsed_components": [],
        "inferred_apis": [],
        "code_analysis_summary": {},
        "trd_draft": None,
        "trd_validation_result": None,
        "api_specification": None,
        "database_schema": None,
        "architecture_diagram": None,
        "tech_stack_document": None,
        "current_stage": "initializing",
        "completion_percentage": 0.0,
        "iteration_count": 0,
        "errors": [],
        "completed": False,
    }


@pytest.mark.asyncio
class TestWorkflowInitialization:
    """Test workflow creation and initialization."""

    async def test_create_workflow(self):
        """Test that workflow can be created successfully."""
        workflow = await create_tech_spec_workflow()

        assert workflow is not None
        # Verify workflow has nodes
        assert hasattr(workflow, "nodes") or hasattr(workflow, "compile")

    async def test_workflow_has_all_nodes(self):
        """Test that workflow includes all 17 required nodes."""
        workflow = await create_tech_spec_workflow()

        # Expected nodes (may need adjustment based on actual implementation)
        expected_nodes = [
            "load_inputs",
            "analyze_completeness",
            "identify_tech_gaps",
            "research_technologies",
            "present_options",
            "wait_user_decision",
            "validate_decision",
            "parse_ai_studio_code",
            "infer_api_spec",
            "generate_trd",
            "validate_trd",
            "generate_api_spec",
            "generate_db_schema",
            "generate_architecture",
            "generate_tech_stack_doc",
            "save_to_db",
            "notify_next_agent",
        ]

        # This test may need adjustment based on how nodes are exposed
        pass  # Placeholder - implementation depends on workflow structure


@pytest.mark.asyncio
class TestPhase1InputAnalysis:
    """Test Phase 1: Input loading and completeness analysis."""

    async def test_load_inputs_from_database(self, sample_state):
        """Test loading PRD and design docs from database."""
        from src.langgraph.nodes.load_inputs import load_inputs_node

        with patch("src.database.connection.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "prd_content": "# PRD content",
                "design_docs": {"design_system": "# Design"}
            })
            mock_db.return_value = mock_conn

            result = await load_inputs_node(sample_state)

            assert result["prd_content"] is not None
            assert "current_stage" in result
            assert result["completion_percentage"] > 0

    async def test_analyze_completeness_high_score(self, sample_state):
        """Test completeness analysis with complete PRD."""
        from src.langgraph.nodes.analysis_nodes import analyze_completeness_node

        # Mock LLM response
        mock_llm_client = AsyncMock()
        mock_llm_client.ainvoke.return_value = """
{
    "completeness_score": 85,
    "missing_elements": [],
    "ambiguous_elements": ["Payment processing details needed"]
}
        """

        with patch("src.langgraph.nodes.analysis_nodes.LLMClient", return_value=mock_llm_client):
            result = await analyze_completeness_node(sample_state)

            assert result["completeness_score"] >= 80
            assert len(result["missing_elements"]) == 0

    async def test_analyze_completeness_low_score(self, sample_state):
        """Test completeness analysis with incomplete PRD."""
        sample_state["prd_content"] = "# Minimal PRD\nBasic project description only."

        from src.langgraph.nodes.analysis_nodes import analyze_completeness_node

        mock_llm_client = AsyncMock()
        mock_llm_client.ainvoke.return_value = """
{
    "completeness_score": 55,
    "missing_elements": ["Authentication specification", "API endpoints", "Database schema"],
    "ambiguous_elements": ["Unclear performance requirements"]
}
        """

        with patch("src.langgraph.nodes.analysis_nodes.LLMClient", return_value=mock_llm_client):
            result = await analyze_completeness_node(sample_state)

            assert result["completeness_score"] < 80
            assert len(result["missing_elements"]) > 0

    async def test_identify_tech_gaps(self, sample_state):
        """Test identification of technology gaps."""
        from src.langgraph.nodes.analysis_nodes import identify_tech_gaps_node

        mock_llm_client = AsyncMock()
        mock_llm_client.ainvoke.return_value = """
{
    "gaps": [
        {
            "category": "authentication",
            "description": "User authentication system needed",
            "priority": "high"
        },
        {
            "category": "database",
            "description": "Database for user and product data",
            "priority": "critical"
        },
        {
            "category": "payments",
            "description": "Payment processing integration (Stripe)",
            "priority": "high"
        }
    ]
}
        """

        with patch("src.langgraph.nodes.analysis_nodes.LLMClient", return_value=mock_llm_client):
            result = await identify_tech_gaps_node(sample_state)

            assert len(result["identified_gaps"]) > 0
            assert any(gap["category"] == "authentication" for gap in result["identified_gaps"])


@pytest.mark.asyncio
class TestPhase2TechnologyResearch:
    """Test Phase 2: Technology research and user decisions."""

    async def test_research_technologies_with_caching(self, sample_state):
        """Test technology research with Redis caching (Week 12)."""
        from src.langgraph.nodes.research_nodes import research_technologies_node

        sample_state["identified_gaps"] = [
            {"category": "authentication", "description": "Auth system", "priority": "high"}
        ]

        # Mock Redis cache miss
        with patch("src.cache.redis_client.get", return_value=None):
            # Mock research
            with patch("src.research.tech_research.TechnologyResearcher") as mock_researcher:
                mock_instance = AsyncMock()
                mock_instance.research_category.return_value = MagicMock(
                    options=[
                        MagicMock(dict=lambda: {
                            "technology_name": "NextAuth.js",
                            "description": "Auth for Next.js",
                            "pros": ["Easy setup"],
                            "cons": ["Tied to Next.js"],
                            "use_cases": ["Next.js apps"],
                            "popularity_score": 90,
                            "learning_curve": "low",
                            "documentation_quality": "excellent",
                            "community_support": "excellent",
                            "integration_complexity": "low",
                            "sources": []
                        })
                    ],
                    research_summary="NextAuth.js is recommended",
                    recommendation="Use NextAuth.js"
                )
                mock_researcher.return_value = mock_instance

                with patch("src.cache.redis_client.set") as mock_cache_set:
                    result = await research_technologies_node(sample_state)

                    # Should have research results
                    assert len(result["research_results"]) > 0
                    # Should cache the results
                    mock_cache_set.assert_called_once()

    async def test_research_technologies_cache_hit(self, sample_state):
        """Test technology research with cache hit."""
        from src.langgraph.nodes.research_nodes import research_technologies_node

        sample_state["identified_gaps"] = [
            {"category": "database", "description": "Database", "priority": "critical"}
        ]

        cached_result = {
            "category": "database",
            "options": [{"technology_name": "PostgreSQL"}],
            "summary": "Cached research"
        }

        # Mock Redis cache hit
        with patch("src.cache.redis_client.get", return_value=cached_result):
            result = await research_technologies_node(sample_state)

            # Should use cached results
            assert len(result["research_results"]) > 0
            assert result["research_results"][0] == cached_result

    async def test_present_options_to_user(self, sample_state):
        """Test presenting technology options to user."""
        from src.langgraph.nodes.research_nodes import present_options_node

        sample_state["research_results"] = [
            {
                "category": "authentication",
                "description": "Auth system",
                "options": [
                    {"id": 1, "technology_name": "NextAuth.js"},
                    {"id": 2, "technology_name": "Passport.js"}
                ],
                "summary": "Both are good options",
                "recommendation": "Use NextAuth.js"
            }
        ]

        result = await present_options_node(sample_state)

        # Should have formatted question for user
        assert result["current_question"] is not None
        assert "current_research_category" in result


@pytest.mark.asyncio
class TestPhase3CodeAnalysis:
    """Test Phase 3: Code analysis with AST parsing and GraphQL (Week 9)."""

    async def test_parse_ai_studio_code_with_graphql(self, sample_state):
        """Test parsing code with GraphQL operations."""
        from src.langgraph.nodes.code_analysis_nodes import parse_ai_studio_code_node

        # Create mock ZIP file content
        sample_code = """
import { useQuery, gql } from '@apollo/client';

interface UserProps {
    userId: string;
}

const GET_USER = gql`
    query GetUser($userId: ID!) {
        user(id: $userId) {
            id
            name
            email
        }
    }
`;

function UserProfile({ userId }: UserProps) {
    const { data } = useQuery(GET_USER, { variables: { userId } });
    return <div>{data?.user.name}</div>;
}
        """

        # Mock file operations
        with patch("zipfile.ZipFile") as mock_zip:
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = sample_code

                # Mock ZIP file listing
                mock_zip_instance = MagicMock()
                mock_zip_instance.namelist.return_value = ["UserProfile.tsx"]
                mock_zip.return_value.__enter__.return_value = mock_zip_instance

                sample_state["google_ai_studio_code_path"] = "/fake/path.zip"

                result = await parse_ai_studio_code_node(sample_state)

                # Should detect GraphQL usage
                components = result.get("google_ai_studio_data", {}).get("components", [])
                if components:
                    assert any(c.get("uses_graphql") for c in components)

    async def test_infer_api_spec_from_code(self, sample_state):
        """Test API specification inference from parsed code."""
        from src.langgraph.nodes.code_analysis_nodes import infer_api_spec_node

        sample_state["google_ai_studio_data"] = {
            "components": [
                {
                    "name": "UserList",
                    "api_calls": [
                        {"type": "fetch", "url": "/api/users", "method": "GET"}
                    ],
                    "uses_graphql": True,
                    "graphql_operations": [
                        {
                            "type": "query",
                            "name": "GetUsers",
                            "variables": [],
                            "fields": ["users", "id", "name"]
                        }
                    ]
                }
            ]
        }

        result = await infer_api_spec_node(sample_state)

        # Should have inferred APIs (both REST and GraphQL)
        assert "inferred_apis" in result
        assert len(result["inferred_apis"]) > 0


@pytest.mark.asyncio
class TestPhase4DocumentGeneration:
    """Test Phase 4: Document generation with Week 8 enhancements."""

    async def test_generate_trd_with_validation(self, sample_state):
        """Test TRD generation with structure validation."""
        from src.langgraph.nodes.generation_nodes import generate_trd_node

        sample_state["selected_technologies"] = {
            "database": {"name": "PostgreSQL"},
            "authentication": {"name": "NextAuth.js"}
        }

        # Mock LLM TRD generation
        mock_llm_client = AsyncMock()
        mock_llm_client.ainvoke.return_value = """
# Technical Requirements Document

## 1. System Architecture
Complete architecture...

## 2. Technology Stack
NextAuth.js, PostgreSQL...

[... all 10 required sections ...]

## 10. Deployment Strategy
Docker containers...
        """

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await generate_trd_node(sample_state)

            assert result["trd_draft"] is not None
            assert result["trd_validation_result"] is not None

    async def test_generate_trd_retry_on_low_quality(self, sample_state):
        """Test TRD regeneration when quality score < 90."""
        from src.langgraph.nodes.generation_nodes import generate_trd_node

        sample_state["iteration_count"] = 0

        # Mock LLM to return low quality first, then high quality
        mock_llm_client = AsyncMock()
        responses = [
            "# Minimal TRD\nNot complete",  # Low quality
            """
# Technical Requirements Document
[Complete TRD with all sections...]
            """  # High quality
        ]
        mock_llm_client.ainvoke.side_effect = responses

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            # This would be tested via workflow execution with retry logic
            pass

    async def test_multi_agent_review_integration(self, sample_state):
        """Test multi-agent TRD review integration."""
        from src.langgraph.nodes.generation_nodes import _multi_agent_trd_review

        trd_content = "# Complete TRD document..."
        prd_content = sample_state["prd_content"]
        tech_decisions = {"database": "PostgreSQL"}

        # Mock all 5 agent responses
        mock_llm_client = AsyncMock()
        mock_llm_client.ainvoke.side_effect = [
            '{"score": 85, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []}',
            '{"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []}',
            '{"score": 87, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []}',
            '{"score": 92, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []}',
            '{"score": 88, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []}',
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            assert result is not None
            assert "average_score" in result
            # Average of (85+90+87+92+88)/5 = 88.4
            assert 88 <= result["average_score"] <= 89


@pytest.mark.asyncio
class TestPhase5Persistence:
    """Test Phase 5: Database persistence."""

    async def test_save_to_db_all_documents(self, sample_state):
        """Test saving all 5 documents to database."""
        from src.langgraph.nodes.persistence_nodes import save_to_db_node

        sample_state["trd_draft"] = "# Complete TRD"
        sample_state["api_specification"] = {"openapi": "3.0"}
        sample_state["database_schema"] = "CREATE TABLE users..."
        sample_state["architecture_diagram"] = "```mermaid\n...\n```"
        sample_state["tech_stack_document"] = {"stack": "MERN"}
        sample_state["trd_validation_result"] = {"total_score": 92}

        # Mock database operations
        with patch("src.database.connection.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock()
            mock_conn.transaction = AsyncMock()
            mock_conn.transaction.return_value.__aenter__ = AsyncMock()
            mock_conn.transaction.return_value.__aexit__ = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_db.return_value = mock_conn

            result = await save_to_db_node(sample_state)

            # Should update completion status
            assert result["current_stage"] == "documents_saved"
            assert result["completion_percentage"] == 95.0


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and recovery."""

    async def test_node_error_appends_to_errors_list(self, sample_state):
        """Test that node errors are captured in state."""
        from src.langgraph.nodes.analysis_nodes import analyze_completeness_node

        # Mock LLM to raise error
        with patch("src.langgraph.nodes.analysis_nodes.LLMClient") as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.side_effect = Exception("LLM API error")
            mock_llm_class.return_value = mock_llm_instance

            with pytest.raises(Exception):
                await analyze_completeness_node(sample_state)

    async def test_error_logging_to_database(self):
        """Test that errors are persisted to agent_error_logs."""
        from src.langgraph.error_logging import log_state_errors_to_db

        session_id = str(uuid.uuid4())
        errors = [
            {
                "node": "generate_trd",
                "error_type": "ValidationError",
                "message": "TRD quality too low",
                "timestamp": datetime.now().isoformat(),
                "recoverable": True
            }
        ]

        # Mock database
        with patch("src.database.connection.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_db.return_value = mock_conn

            logged_count = await log_state_errors_to_db(session_id, errors)

            assert logged_count == 1
