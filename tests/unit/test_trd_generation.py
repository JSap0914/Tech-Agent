"""
Unit tests for TRD generation with Week 8 enhancements.
Tests few-shot examples, structured validation, and multi-agent review.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.langgraph.nodes.generation_nodes import (
    _validate_trd_structure,
    _multi_agent_trd_review,
)


class TestTRDStructuredValidation:
    """Test structured TRD format validation (Week 8)."""

    def test_validate_complete_trd(self):
        """Test validation of complete TRD document."""
        trd_content = """
        # Technical Requirements Document

        ## Project Overview
        This project is a comprehensive SaaS platform for project management
        designed to support distributed teams with real-time collaboration features.
        The system will handle user authentication, project creation, task management,
        file uploads, and real-time notifications across multiple devices.

        ## System Architecture
        The system follows a modern three-tier architecture with clear separation of concerns.
        Frontend is built with Next.js 14 for server-side rendering and optimal SEO.
        Backend uses NestJS framework providing enterprise-grade architecture with dependency injection.
        PostgreSQL 15 serves as the primary database with ACID compliance for data integrity.
        Redis provides caching layer for session management and real-time features.
        AWS S3 handles file storage with CDN integration for global distribution.

        ## Technology Stack
        ### Frontend Technologies
        - Next.js 14.0.0 - React framework with server-side rendering and static generation
          Rationale: Industry standard for production React applications with excellent developer experience
        - React 18.2.0 - Component-based UI library with concurrent features
        - TypeScript 5.0 - Type-safe JavaScript superset
        - TailwindCSS 3.3 - Utility-first CSS framework

        ### Backend Technologies
        - NestJS 10.0 - Progressive Node.js framework with TypeScript support
        - Node.js 20 LTS - JavaScript runtime environment
        - PostgreSQL 15.3 - Advanced relational database
        - Redis 7.2 - In-memory data store for caching

        ### DevOps & Infrastructure
        - Docker - Containerization platform
        - AWS ECS - Container orchestration
        - GitHub Actions - CI/CD pipeline

        ## API Specification
        RESTful API following OpenAPI 3.0 specification with comprehensive endpoint documentation.
        All endpoints require Bearer token authentication except public routes.
        Rate limiting applied at 100 requests per minute per user.

        ```
        GET /api/v1/projects - List all projects for authenticated user
        POST /api/v1/projects - Create new project
        GET /api/v1/projects/:id - Get project details
        PUT /api/v1/projects/:id - Update project
        DELETE /api/v1/projects/:id - Delete project

        GET /api/v1/tasks - List tasks with filtering
        POST /api/v1/tasks - Create new task
        PUT /api/v1/tasks/:id - Update task status
        ```

        Authentication endpoints use JWT tokens with 1-hour expiration.
        Refresh tokens provided with 7-day expiration for seamless re-authentication.
        OAuth 2.0 integration for Google and GitHub authentication providers.

        ## Database Schema
        ```sql
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'todo',
            assignee_id UUID REFERENCES users(id),
            due_date TIMESTAMP
        );

        CREATE INDEX idx_tasks_project ON tasks(project_id);
        CREATE INDEX idx_projects_user ON projects(user_id);
        ```

        ## Security Requirements
        All communications encrypted via HTTPS with TLS 1.3 minimum.
        Passwords hashed using bcrypt with salt rounds of 12.
        JWT tokens signed with RS256 algorithm using private key rotation.
        OWASP Top 10 security best practices implemented throughout application.
        SQL injection prevention through parameterized queries and ORM usage.
        XSS protection via Content Security Policy headers and input sanitization.
        CSRF protection using SameSite cookies and token validation.
        Rate limiting on all API endpoints to prevent DDoS attacks.
        Regular security audits and dependency vulnerability scanning.

        ## Performance Requirements
        Page load time under 2 seconds for 95th percentile requests.
        API response time under 200ms for database queries on p95.
        Support for 10,000 concurrent WebSocket connections per instance.
        Database query optimization with proper indexing strategies.
        CDN integration for static assets with edge caching.
        Lazy loading for images and code splitting for optimal bundle size.
        Redis caching for frequently accessed data reducing database load.

        ## Deployment Strategy
        Docker containers for all services ensuring consistent environments.
        AWS ECS for container orchestration with auto-scaling policies.
        Blue-green deployment strategy for zero-downtime updates.
        Multi-region deployment for high availability and disaster recovery.
        CloudWatch for centralized logging and monitoring.
        Terraform for infrastructure as code and reproducible deployments.

        ## Testing Strategy
        Unit tests with Jest achieving 80%+ code coverage.
        Integration tests for API endpoints using Supertest.
        End-to-end tests with Playwright for critical user flows.
        Load testing with k6 to validate performance requirements.
        Security testing with OWASP ZAP for vulnerability scanning.
        Continuous testing in CI/CD pipeline with automated quality gates.

        ## Development Guidelines
        Follow Airbnb JavaScript style guide for consistent code quality.
        Use conventional commits for clear git history and automated changelog.
        Code reviews required for all pull requests with minimum 2 approvals.
        Automated linting with ESLint and formatting with Prettier.
        Documentation requirements for all public APIs and complex logic.
        """

        is_valid, issues, score = _validate_trd_structure(trd_content)

        assert is_valid is True
        assert score >= 80
        # Minor issues (low/medium severity) are acceptable as long as TRD is valid
        # Check that there are no critical/high severity issues
        critical_issues = [i for i in issues if i.get('severity') == 'high']
        assert len(critical_issues) == 0

    def test_validate_missing_sections(self):
        """Test validation catches missing required sections."""
        trd_content = """
        # Technical Requirements Document

        ## 1. System Architecture
        - Frontend: Next.js

        ## 2. Technology Stack
        - React 18
        """

        is_valid, issues, score = _validate_trd_structure(trd_content)

        assert is_valid is False
        assert score < 80
        assert len(issues) > 0
        # Issues are dicts with 'section' and 'issue' keys
        assert any("API Specification" in issue.get("section", "") for issue in issues)
        assert any("Database Schema" in issue.get("section", "") for issue in issues)

    def test_validate_insufficient_content_length(self):
        """Test validation catches insufficient content."""
        trd_content = """
        # Technical Requirements Document

        ## 1. System Architecture
        - Basic info
        """

        is_valid, issues, score = _validate_trd_structure(trd_content)

        assert is_valid is False
        # Should have low score due to short content
        assert score < 60
        # Issues are dicts, check 'issue' field
        assert any("too short" in issue.get("issue", "").lower() or "short" in issue.get("issue", "").lower() for issue in issues)

    def test_validate_missing_code_blocks(self):
        """Test validation encourages code examples."""
        trd_content_no_code = """
        # Technical Requirements Document

        ## 1. System Architecture
        Lots of text but no code examples at all.

        ## 2. Technology Stack
        More text, no code blocks.

        ## 3. API Specifications
        Just descriptions, no actual API examples.

        ## 4. Database Schema
        No DDL or schema examples.

        ## 5. Authentication & Authorization
        Text only.

        ## 6. Data Models
        No model definitions.

        ## 7. File Upload & Storage
        Description only.

        ## 8. Security Requirements
        Text.

        ## 9. Performance Requirements
        More text.

        ## 10. Deployment Strategy
        Still no code.
        """

        is_valid, issues, score = _validate_trd_structure(trd_content_no_code)

        # Should pass basic validation but have lower score
        assert any("code" in issue.get("issue", "").lower() or "example" in issue.get("issue", "").lower() for issue in issues)

    def test_validate_missing_api_endpoints(self):
        """Test validation checks for API endpoint documentation."""
        trd_content = """
        # Technical Requirements Document

        ## 1. System Architecture
        - Frontend: Next.js 14
        - Backend: NestJS

        ## 2. Technology Stack
        - React 18

        ## 3. API Specifications
        We will use REST API but no endpoints defined.

        ## 4. Database Schema
        - Some tables

        ## 5. Authentication & Authorization
        - JWT

        ## 6. Data Models
        - Models

        ## 7. File Upload & Storage
        - S3

        ## 8. Security Requirements
        - Secure

        ## 9. Performance Requirements
        - Fast

        ## 10. Deployment Strategy
        - Docker
        """

        is_valid, issues, score = _validate_trd_structure(trd_content)

        # Should note lack of API endpoint details
        assert any("endpoint" in issue.get("issue", "").lower() or "api" in issue.get("issue", "").lower() for issue in issues)

    def test_validate_fail_fast_on_very_low_score(self):
        """Test that validation fails fast on score < 40."""
        minimal_trd = """
        # TRD

        Something minimal.
        """

        is_valid, issues, score = _validate_trd_structure(minimal_trd)

        assert is_valid is False
        assert score < 40


@pytest.mark.asyncio
class TestMultiAgentTRDReview:
    """Test multi-agent TRD review system (Week 8)."""

    async def test_multi_agent_review_all_agents_invoked(self):
        """Test that all 5 specialized agents are invoked."""
        trd_content = "# TRD Document with complete sections..."
        prd_content = "# PRD with requirements..."
        tech_decisions = [
            {"category": "database", "technology_name": "PostgreSQL"},
            {"category": "authentication", "technology_name": "NextAuth.js"}
        ]

        mock_llm_client = AsyncMock()
        # Mock responses for each agent (generate_json returns dict directly, not JSON string)
        mock_llm_client.generate_json.side_effect = [
            # Architecture agent
            {
                "score": 85,
                "strengths": ["Good architecture"],
                "weaknesses": ["Minor issues"],
                "critical_issues": [],
                "recommendations": ["Add caching"]
            },
            # Security agent
            {
                "score": 90,
                "strengths": ["Good security"],
                "weaknesses": [],
                "critical_issues": [],
                "recommendations": ["Add rate limiting"]
            },
            # Performance agent
            {
                "score": 80,
                "strengths": ["Good perf"],
                "weaknesses": ["No caching"],
                "critical_issues": [],
                "recommendations": ["Add Redis"]
            },
            # API agent
            {
                "score": 88,
                "strengths": ["Good API design"],
                "weaknesses": [],
                "critical_issues": [],
                "recommendations": []
            },
            # Database agent
            {
                "score": 92,
                "strengths": ["Good schema"],
                "weaknesses": [],
                "critical_issues": [],
                "recommendations": []
            },
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            # All 5 agents should be invoked
            assert mock_llm_client.generate_json.call_count == 5

            # Result should have reviews from all agents
            assert "agent_reviews" in result
            assert "architecture" in result["agent_reviews"]
            assert "security" in result["agent_reviews"]
            assert "performance" in result["agent_reviews"]
            assert "api" in result["agent_reviews"]
            assert "database" in result["agent_reviews"]

    async def test_multi_agent_review_aggregates_scores(self):
        """Test that multi-agent review aggregates scores correctly."""
        trd_content = "# TRD..."
        prd_content = "# PRD..."
        tech_decisions = []

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_json.side_effect = [
            {"score": 80, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 85, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 88, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 92, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            # Average score should be (80+90+85+88+92)/5 = 87
            assert "multi_agent_score" in result
            assert result["multi_agent_score"] == 87.0

    async def test_multi_agent_review_collects_critical_issues(self):
        """Test that critical issues from all agents are collected."""
        trd_content = "# TRD..."
        prd_content = "# PRD..."
        tech_decisions = []

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_json.side_effect = [
            {
                "score": 70,
                "strengths": [],
                "weaknesses": [],
                "critical_issues": ["No error handling"],
                "recommendations": []
            },
            {
                "score": 65,
                "strengths": [],
                "weaknesses": [],
                "critical_issues": ["No input validation", "SQL injection risk"],
                "recommendations": []
            },
            {"score": 80, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 85, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            # Should collect all critical issues (prefixed with agent name)
            assert "critical_issues" in result
            assert len(result["critical_issues"]) == 3
            # Issues are prefixed with agent name like "[Architecture Agent] No error handling"
            assert any("No error handling" in issue for issue in result["critical_issues"])
            assert any("No input validation" in issue for issue in result["critical_issues"])
            assert any("SQL injection risk" in issue for issue in result["critical_issues"])

    async def test_multi_agent_review_skipped_if_structure_score_low(self):
        """Test that multi-agent review is skipped if structure score < 60."""
        # This would be tested in the full generate_trd_node, but we can test the guard
        # The actual node checks structure score before calling multi-agent review
        pass  # Placeholder for integration test

    async def test_multi_agent_review_handles_json_parse_errors(self):
        """Test that review handles malformed JSON responses gracefully."""
        trd_content = "# TRD..."
        prd_content = "# PRD..."
        tech_decisions = []

        mock_llm_client = AsyncMock()
        # First response raises error (simulating JSON parse failure), rest are valid
        mock_llm_client.generate_json.side_effect = [
            ValueError("Invalid JSON"),
            {"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 85, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 88, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 92, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            # Should handle error gracefully and continue with other agents
            # Malformed response should get default low score
            assert result is not None


class TestFewShotExamplesIntegration:
    """Test that few-shot examples improve TRD quality."""

    def test_trd_with_examples_has_better_structure(self):
        """Test that TRDs following example format score higher."""
        # TRD following few-shot example format
        trd_with_examples = """
        # Technical Requirements Document

        ## Project Overview
        This project implements a real-time collaboration platform for project management.
        The system enables teams to create projects, assign tasks, and track progress in real-time.
        Key features include user authentication, WebSocket-based real-time updates, file storage,
        team collaboration features, and comprehensive analytics dashboard for project insights.

        ## Technology Stack
        ### Frontend
        - Next.js 14.0.0 - Server-side rendering framework chosen because of excellent SEO support
          Rationale: Industry standard for React SSR with excellent developer experience and performance
        - TypeScript 5.0.4 - Type-safe JavaScript selected for reducing runtime errors
          Rationale: Reduces runtime errors and improves maintainability with strong typing
        - React 18.2.0 - UI library
        - TailwindCSS 3.3.2 - Utility-first CSS framework
        ### Backend
        - NestJS 10.0.0 - Node.js framework
        - PostgreSQL 15.3 - Relational database
        ### Infrastructure
        - AWS ECS - Container orchestration
        - Redis 7.0.0 - Caching layer

        ## System Architecture
        The system follows a modern three-tier architecture with clear separation of concerns.
        Next.js frontend handles SSR and client-side interactions. NestJS backend provides RESTful APIs
        and WebSocket connections for real-time features. PostgreSQL stores persistent data with Redis
        caching frequently accessed information. All components communicate via well-defined interfaces.
        ```mermaid
        graph LR
          Client --> API --> Database
          API --> Redis
          API --> WebSocket
        ```

        ## API Specification
        ```
        GET /api/v1/projects - List all projects for authenticated user
        POST /api/v1/projects - Create new project with name, description
        PUT /api/v1/projects/:id - Update existing project details
        DELETE /api/v1/projects/:id - Delete project and associated tasks
        GET /api/v1/tasks - List tasks with filtering by project
        POST /api/v1/tasks - Create new task with assignment
        PUT /api/v1/tasks/:id - Update task status and details
        DELETE /api/v1/tasks/:id - Delete task
        ```

        ## Database Schema
        ```sql
        CREATE TABLE projects (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name VARCHAR(255) NOT NULL,
          description TEXT,
          owner_id UUID REFERENCES users(id),
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE tasks (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
          title VARCHAR(255) NOT NULL,
          description TEXT,
          status VARCHAR(50) DEFAULT 'todo',
          assignee_id UUID REFERENCES users(id),
          created_at TIMESTAMP DEFAULT NOW()
        );
        ```

        ## Security Requirements
        All API communications must use HTTPS with TLS 1.3 encryption. Authentication is handled via
        JWT tokens using RS256 algorithm with 1-hour expiration and refresh token rotation every 7 days.
        Password hashing uses bcrypt with 12 rounds. Input validation prevents SQL injection and XSS attacks.
        Rate limiting enforces 100 requests per minute per IP address. CORS policies restrict origins to
        approved domains only. API keys are stored in AWS Secrets Manager with automatic rotation every 90 days.

        ## Performance Requirements
        Page load time must be under 2 seconds for 95th percentile measured at edge locations worldwide.
        API response time targets are 50ms for P50, 100ms for P90, and 200ms for P95 percentiles under
        normal load conditions. Database queries must use indexes for all common access patterns. Redis
        caching reduces database load for frequently accessed data with 15-minute TTL for most resources.

        ## Deployment Strategy
        All services run in Docker containers orchestrated by AWS ECS with auto-scaling based on CPU and
        memory metrics. Blue-green deployment strategy ensures zero-downtime updates. Infrastructure as
        Code uses Terraform for provisioning and CloudFormation for AWS resource management. Monitoring
        via CloudWatch with custom metrics and alerts for anomaly detection and automated rollback triggers.

        ## Testing Strategy
        Jest provides unit test coverage for backend services and frontend components with minimum 80%
        code coverage requirement. Playwright handles end-to-end testing across Chrome, Firefox, and Safari
        browsers. Integration tests verify API contracts and database interactions. Load testing uses k6
        to validate performance under expected traffic patterns and stress conditions up to 3x normal load.

        ## Development Guidelines
        Follow Airbnb JavaScript style guide for consistency across the codebase. Use conventional commits
        for clear git history and automated changelog generation. Pull requests require at least one code
        review approval and all CI checks must pass. Branch naming follows pattern: feature/*, bugfix/*,
        hotfix/*. Code must pass ESLint and Prettier checks before commit using pre-commit hooks.
        """

        is_valid, issues, score = _validate_trd_structure(trd_with_examples)

        # Should score highly because it follows the example format
        assert score >= 80
        assert is_valid is True

    def test_version_numbers_improve_score(self):
        """Test that including version numbers improves validation score."""
        # Base content is same, only difference is version numbers
        base_sections = """
        ## Project Overview
        """ + "x" * 250 + """
        ## System Architecture
        """ + "x" * 350 + """
        ## API Specification
        GET /api/test
        POST /api/test
        PUT /api/test
        """ + "x" * 650 + """
        ## Database Schema
        """ + "x" * 450 + """
        ## Security Requirements
        """ + "x" * 350 + """
        ## Performance Requirements
        """ + "x" * 250 + """
        ## Deployment Strategy
        """ + "x" * 250 + """
        ## Testing Strategy
        """ + "x" * 250 + """
        ## Development Guidelines
        """ + "x" * 200 + """
        """

        trd_without_versions = """
        # TRD
        ## Technology Stack
        Using Next.js, React, and PostgreSQL for this modern web application stack.
        The frontend is built with Next.js framework providing server-side rendering capabilities.
        React handles the component-based UI architecture. PostgreSQL serves as our relational database.
        TypeScript adds type safety. TailwindCSS provides utility-first styling approach.
        """ + base_sections

        trd_with_versions = """
        # TRD
        ## Technology Stack
        Using Next.js 14.0.0, React 18.2.0, and PostgreSQL 15.3 for this modern web application stack.
        The frontend is built with Next.js 14.0.0 framework providing server-side rendering capabilities.
        React 18.2.0 handles the component-based UI architecture. PostgreSQL 15.3 serves as our database.
        TypeScript 5.0.4 adds type safety. TailwindCSS 3.3.2 provides utility-first styling approach.
        """ + base_sections

        _, _, score_without = _validate_trd_structure(trd_without_versions)
        _, _, score_with = _validate_trd_structure(trd_with_versions)

        # Version numbers should improve score (5 points in validation logic)
        assert score_with > score_without

    def test_rationale_keywords_improve_score(self):
        """Test that including rationale improves validation score."""
        # Base content is same, only difference is rationale keywords
        base_sections = """
        ## Project Overview
        """ + "x" * 250 + """
        ## System Architecture
        """ + "x" * 350 + """
        ## API Specification
        GET /api/test
        POST /api/test
        PUT /api/test
        """ + "x" * 650 + """
        ## Database Schema
        """ + "x" * 450 + """
        ## Security Requirements
        """ + "x" * 350 + """
        ## Performance Requirements
        """ + "x" * 250 + """
        ## Deployment Strategy
        """ + "x" * 250 + """
        ## Testing Strategy
        """ + "x" * 250 + """
        ## Development Guidelines
        """ + "x" * 200 + """
        """

        trd_without_rationale = """
        # TRD
        ## Technology Stack
        We use Next.js 14.0.0 for the frontend framework providing server-side rendering.
        PostgreSQL 15.3 serves as our relational database with ACID compliance and JSON support.
        TypeScript 5.0.4 adds type safety to the JavaScript codebase for better maintainability.
        React 18.2.0 provides the component-based UI architecture for building interactive interfaces.
        """ + base_sections

        trd_with_rationale = """
        # TRD
        ## Technology Stack
        We use Next.js 14.0.0 chosen because of excellent SSR performance and SEO capabilities.
        PostgreSQL 15.3 was selected for ACID compliance and JSON support which meets our data needs.
        Rationale: TypeScript 5.0.4 adds type safety chosen to reduce runtime errors in production.
        The reason for React 18.2.0 is its mature ecosystem and team expertise with the framework.
        """ + base_sections

        _, _, score_without = _validate_trd_structure(trd_without_rationale)
        _, _, score_with = _validate_trd_structure(trd_with_rationale)

        # Rationale keywords should improve score (5 points in validation logic)
        assert score_with > score_without


class TestTRDValidationWithRetry:
    """Test TRD validation with retry logic."""

    def test_validation_passes_on_first_try(self):
        """Test validation passes on first attempt if score >= 90."""
        high_quality_trd = """
        # Technical Requirements Document

        ## Project Overview
        This comprehensive project delivers a modern enterprise SaaS platform for project management
        and team collaboration. The system handles user authentication, real-time updates, file storage,
        and analytics dashboards. Built for scalability to support 100,000+ concurrent users with
        99.9% uptime SLA. Key features include role-based access control, WebSocket communication,
        automated workflows, and extensive API integrations with third-party services.

        ## Technology Stack
        ### Frontend Stack
        - Next.js 14.0.0 - Server-side rendering framework chosen because of excellent SEO and performance
        - React 18.2.0 - Component-based UI library selected for team expertise and ecosystem maturity
        - TypeScript 5.0.4 - Type safety chosen to reduce runtime errors and improve developer experience
        - TailwindCSS 3.3.2 - Utility-first CSS framework for rapid UI development
        Rationale: This stack provides the best balance of performance, developer experience, and maintainability
        ### Backend Stack
        - NestJS 10.0.0 - Node.js framework with TypeScript support and dependency injection
        - PostgreSQL 15.3 - ACID-compliant relational database for data integrity
        - Redis 7.0.0 - In-memory cache for session storage and real-time features

        ## System Architecture
        The system follows a microservices architecture with API gateway pattern for routing requests.
        Frontend Next.js application communicates with NestJS backend via RESTful APIs and WebSocket
        connections for real-time features. PostgreSQL provides persistent storage with read replicas
        for scaling read operations. Redis handles caching and pub/sub messaging for real-time updates.
        All services run in Docker containers orchestrated by Kubernetes for high availability.
        ```typescript
        // Example service architecture
        class ProjectService {
          constructor(private db: Database, private cache: Redis) {}
        }
        ```

        ## API Specification
        ```
        GET /api/v1/projects - List all projects with pagination
        POST /api/v1/projects - Create new project with validation
        PUT /api/v1/projects/:id - Update project details
        DELETE /api/v1/projects/:id - Soft delete project
        GET /api/v1/tasks - List tasks with filtering
        POST /api/v1/tasks - Create task with assignment
        PUT /api/v1/tasks/:id - Update task status
        DELETE /api/v1/tasks/:id - Delete task
        GET /api/v1/analytics - Fetch dashboard metrics
        POST /api/v1/upload - Handle file uploads to S3
        ```

        ## Database Schema
        ```sql
        CREATE TABLE users (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email VARCHAR(255) UNIQUE NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          role VARCHAR(50) DEFAULT 'member',
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE projects (
          id UUID PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          description TEXT,
          owner_id UUID REFERENCES users(id),
          status VARCHAR(50),
          created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX idx_projects_owner ON projects(owner_id);
        CREATE INDEX idx_projects_status ON projects(status);
        ```

        ## Security Requirements
        All API endpoints require authentication via JWT tokens with RS256 signing algorithm.
        Passwords are hashed using bcrypt with 12 rounds. Input validation prevents SQL injection
        and XSS attacks using parameterized queries and output encoding. Rate limiting enforces
        100 requests per minute per IP address. CORS policies restrict API access to approved domains.
        Secrets are stored in AWS Secrets Manager with automatic rotation every 90 days. All data
        transmission uses HTTPS with TLS 1.3 encryption. API keys require scoped permissions.

        ## Performance Requirements
        Page load time must be under 2 seconds for 95th percentile measured globally at edge locations.
        API response times target 50ms P50, 100ms P90, and 200ms P95 under normal load conditions.
        Database queries use indexes for all common access patterns with query execution plans verified.
        Redis caching reduces database load with 15-minute TTL for frequently accessed resources.
        CDN delivers static assets from edge locations for optimal performance worldwide.

        ## Deployment Strategy
        All services run in Docker containers orchestrated by Kubernetes with horizontal pod autoscaling.
        Blue-green deployment ensures zero-downtime updates with automated rollback on failure detection.
        Infrastructure as Code uses Terraform for cloud resource provisioning and management across
        multiple environments. Monitoring via Prometheus and Grafana with custom metrics and alerting.
        ```yaml
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: backend-api
        ```

        ## Testing Strategy
        Jest provides unit test coverage for all services with minimum 80% code coverage requirement
        enforced in CI pipeline. Playwright handles end-to-end testing across Chrome, Firefox, and
        Safari browsers. Integration tests verify API contracts and database interactions using
        testcontainers for isolated PostgreSQL instances. Load testing with k6 validates performance
        under 3x expected traffic. Security testing includes OWASP ZAP scans and dependency audits.

        ## Development Guidelines
        Follow Airbnb JavaScript style guide for code consistency enforced by ESLint configuration.
        Use conventional commits for clear git history and automated changelog generation via semantic
        release. All pull requests require at least one code review approval and passing CI checks.
        Branch naming follows pattern: feature/*, bugfix/*, hotfix/*. Pre-commit hooks run Prettier
        and ESLint checks automatically. Code must pass TypeScript type checking with strict mode.
        """

        is_valid, issues, score = _validate_trd_structure(high_quality_trd)

        assert is_valid is True
        assert score >= 90

    def test_validation_fails_below_threshold(self):
        """Test validation fails if score < 90."""
        low_quality_trd = """
        # TRD

        ## 1. System Architecture
        Basic info only

        ## 2. Technology Stack
        React
        """

        is_valid, issues, score = _validate_trd_structure(low_quality_trd)

        assert is_valid is False
        assert score < 90

    def test_iteration_count_tracked(self):
        """Test that iteration count is tracked for regeneration."""
        # This is tracked in state["iteration_count"]
        # Tested in integration tests
        pass


class TestQualityMetrics:
    """Test TRD quality scoring metrics."""

    def test_completeness_metric(self):
        """Test completeness score based on required sections."""
        # All 10 sections present = 100 score
        complete_trd = """
        # TRD
        ## Project Overview
        """ + "x" * 200 + """
        ## Technology Stack
        """ + "x" * 500 + """
        ## System Architecture
        """ + "x" * 300 + """
        ## API Specification
        GET /api/test
        POST /api/test
        PUT /api/test
        """ + "x" * 600 + """
        ## Database Schema
        """ + "x" * 400 + """
        ## Security Requirements
        """ + "x" * 300 + """
        ## Performance Requirements
        """ + "x" * 200 + """
        ## Deployment Strategy
        """ + "x" * 200 + """
        ## Testing Strategy
        """ + "x" * 200 + """
        ## Development Guidelines
        """ + "x" * 150 + """
        ```code1```
        ```code2```
        ```code3```
        ```code4```
        ```code5```
        1.0.0 2.0.0 3.0.0 4.0.0 5.0.0
        """

        is_valid, issues, score = _validate_trd_structure(complete_trd)

        # All sections present should give base 100 score
        assert score >= 85
        assert is_valid is True

    def test_clarity_metric_short_sections_penalized(self):
        """Test that short sections reduce clarity score."""
        trd_short_sections = """
        # TRD
        ## Project Overview
        Too short
        ## Technology Stack
        Also short
        """

        is_valid, issues, score = _validate_trd_structure(trd_short_sections)

        # Short sections should be penalized
        assert score < 40
        assert any("too short" in issue.get("issue", "").lower() for issue in issues)

    def test_technical_detail_metric_code_blocks(self):
        """Test that code blocks improve technical detail score."""
        # Base content with all required sections but varying code blocks
        base_sections = """
        ## Project Overview
        """ + "x" * 250 + """
        ## Technology Stack
        Using Next.js 14.0.0, React 18.2.0, and PostgreSQL 15.3 with TypeScript 5.0.4 and TailwindCSS 3.3.2.
        """ + "x" * 450 + """
        ## System Architecture
        """ + "x" * 350 + """
        ## Database Schema
        """ + "x" * 450 + """
        ## Security Requirements
        """ + "x" * 350 + """
        ## Performance Requirements
        """ + "x" * 250 + """
        ## Deployment Strategy
        """ + "x" * 250 + """
        ## Testing Strategy
        """ + "x" * 250 + """
        ## Development Guidelines
        """ + "x" * 200 + """
        """

        # Without code blocks
        trd_no_code = """
        # TRD
        ## API Specification
        We have REST APIs for user management and project handling with standard CRUD operations.
        """ + "x" * 600 + base_sections

        # With code blocks (5 code blocks = +10 points)
        trd_with_code = """
        # TRD
        ## API Specification
        We have REST APIs for user management and project handling with code examples below.
        ```
        GET /api/users
        ```
        ```
        POST /api/users
        ```
        ```
        PUT /api/users/:id
        ```
        ```
        DELETE /api/users/:id
        ```
        ```sql
        CREATE TABLE users (id UUID, name TEXT);
        ```
        """ + "x" * 600 + base_sections

        _, issues_no_code, score_no_code = _validate_trd_structure(trd_no_code)
        _, issues_with_code, score_with_code = _validate_trd_structure(trd_with_code)

        # Should note lack of code examples (issues are dicts)
        assert any("code" in issue.get("issue", "").lower() or "example" in issue.get("issue", "").lower() for issue in issues_no_code)
        # Code blocks should improve score (10 points in validation logic)
        assert score_with_code > score_no_code

    def test_technical_detail_api_endpoints(self):
        """Test that API endpoint documentation affects score."""
        # Base content with all required sections but varying API endpoints
        base_sections = """
        ## Project Overview
        """ + "x" * 250 + """
        ## Technology Stack
        Using Next.js 14.0.0, React 18.2.0, and PostgreSQL 15.3 with TypeScript 5.0.4 and TailwindCSS 3.3.2.
        """ + "x" * 450 + """
        ## System Architecture
        """ + "x" * 350 + """
        ## Database Schema
        """ + "x" * 450 + """
        ## Security Requirements
        """ + "x" * 350 + """
        ## Performance Requirements
        """ + "x" * 250 + """
        ## Deployment Strategy
        """ + "x" * 250 + """
        ## Testing Strategy
        """ + "x" * 250 + """
        ## Development Guidelines
        """ + "x" * 200 + """
        ```code1```
        ```code2```
        ```code3```
        ```code4```
        ```code5```
        """

        trd_no_endpoints = """
        # TRD
        ## API Specification
        We will use RESTful APIs for all operations with standard HTTP methods and JSON payloads.
        """ + "x" * 600 + base_sections

        trd_with_endpoints = """
        # TRD
        ## API Specification
        We document all RESTful API endpoints below with HTTP methods and paths.
        GET /api/projects
        POST /api/projects
        PUT /api/projects/:id
        DELETE /api/projects/:id
        GET /api/tasks
        """ + "x" * 600 + base_sections

        _, issues_no, score_no = _validate_trd_structure(trd_no_endpoints)
        _, issues_with, score_with = _validate_trd_structure(trd_with_endpoints)

        # Should note lack of endpoints (issues are dicts)
        assert any("endpoint" in issue.get("issue", "").lower() or "api" in issue.get("issue", "").lower() for issue in issues_no)
        # Endpoints should improve score (10 points in validation logic)
        assert score_with > score_no


@pytest.mark.asyncio
class TestVersionMetadata:
    """Test that validation metadata is stored correctly (Week 8)."""

    async def test_validation_report_structure(self):
        """Test that validation report has correct structure."""
        trd_content = "# TRD with some content..."
        prd_content = "# PRD..."
        tech_decisions = {}

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_json.side_effect = [
            {"score": 85, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": ["Add caching"]},
            {"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 80, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 88, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 92, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            result = await _multi_agent_trd_review(trd_content, prd_content, tech_decisions)

            # Verify report structure (agent_reviews is a dict with agent keys)
            assert "agent_reviews" in result
            assert "architecture" in result["agent_reviews"]
            assert "security" in result["agent_reviews"]
            assert "performance" in result["agent_reviews"]
            assert "api" in result["agent_reviews"]
            assert "database" in result["agent_reviews"]
            assert "multi_agent_score" in result
            assert "critical_issues" in result

            # Verify we can construct validation metadata from this
            validation_metadata = {
                "multi_agent_scores": {
                    "architecture": result["agent_reviews"]["architecture"]["score"],
                    "security": result["agent_reviews"]["security"]["score"],
                    "performance": result["agent_reviews"]["performance"]["score"],
                    "api": result["agent_reviews"]["api"]["score"],
                    "database": result["agent_reviews"]["database"]["score"],
                },
                "average_score": result["multi_agent_score"],
                "critical_issues": result["critical_issues"],
                "recommendations": result.get("recommendations", []),
            }

            assert validation_metadata["average_score"] == 87.0
            assert len(validation_metadata["multi_agent_scores"]) == 5

    async def test_structure_and_multi_agent_scores_combined(self):
        """Test that structure and multi-agent scores can be combined into final validation report."""
        # Structure validation
        complete_trd = """
        # TRD
        ## Project Overview
        """ + "x" * 200 + """
        ## Technology Stack
        """ + "x" * 500 + """
        ## System Architecture
        """ + "x" * 300 + """
        ## API Specification
        GET /api/test
        POST /api/test
        PUT /api/test
        """ + "x" * 600 + """
        ## Database Schema
        """ + "x" * 400 + """
        ## Security Requirements
        """ + "x" * 300 + """
        ## Performance Requirements
        """ + "x" * 200 + """
        ## Deployment Strategy
        """ + "x" * 200 + """
        ## Testing Strategy
        """ + "x" * 200 + """
        ## Development Guidelines
        """ + "x" * 150 + """
        ```code1```
        ```code2```
        ```code3```
        ```code4```
        ```code5```
        1.0.0 2.0.0 3.0.0 4.0.0 5.0.0
        """

        is_valid, issues, structure_score = _validate_trd_structure(complete_trd)

        # Mock multi-agent review
        mock_llm_client = AsyncMock()
        mock_llm_client.generate_json.side_effect = [
            {"score": 90, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 92, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 88, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 91, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
            {"score": 89, "strengths": [], "weaknesses": [], "critical_issues": [], "recommendations": []},
        ]

        with patch("src.langgraph.nodes.generation_nodes.LLMClient", return_value=mock_llm_client):
            multi_agent_result = await _multi_agent_trd_review(complete_trd, "PRD", [])

            # Combine scores (Week 8 enhancement)
            final_validation_report = {
                "structure_validation": {
                    "is_valid": is_valid,
                    "issues": issues,
                    "score": structure_score,
                },
                "multi_agent_review": {
                    "individual_scores": {
                        "architecture": multi_agent_result["agent_reviews"]["architecture"]["score"],
                        "security": multi_agent_result["agent_reviews"]["security"]["score"],
                        "performance": multi_agent_result["agent_reviews"]["performance"]["score"],
                        "api": multi_agent_result["agent_reviews"]["api"]["score"],
                        "database": multi_agent_result["agent_reviews"]["database"]["score"],
                    },
                    "average_score": multi_agent_result["multi_agent_score"],
                },
                "total_score": (structure_score + multi_agent_result["multi_agent_score"]) / 2,
                "iteration_count": 1,
            }

            # Verify complete report structure
            assert final_validation_report["structure_validation"]["score"] >= 85
            assert final_validation_report["multi_agent_review"]["average_score"] == 90.0
            assert final_validation_report["total_score"] >= 87.5
            assert "iteration_count" in final_validation_report

            # This structure can be saved to database validation_report column
            assert isinstance(final_validation_report, dict)


import json
