# Project Structure

## Root Directory
```
Tech Agent/
├── .claude/              # Claude Code configuration
├── .github/              # GitHub Actions CI/CD workflows
├── .serena/              # Serena MCP server data
├── alembic/              # Database migration scripts
│   └── versions/         # Migration version files
├── docs/                 # Project documentation
├── monitoring/           # Prometheus & Grafana configs
├── scripts/              # Utility scripts
├── src/                  # Main source code (Python)
├── tests/                # Test suite
├── venv/                 # Python virtual environment
├── .dockerignore         # Docker ignore patterns
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore patterns
├── alembic.ini           # Alembic configuration
├── CLAUDE.md             # Instructions for Claude Code
├── docker-compose.yml    # Multi-container Docker config
├── Dockerfile            # Docker build instructions
├── pyproject.toml        # Python project configuration
├── README.md             # Project README
├── Tech_Spec_Agent_Integration_Plan_FINAL.md  # Integration plan
└── WEEK_*_COMPLETE.md    # Weekly completion status docs
```

## Source Code (`src/`)
```
src/
├── api/
│   └── endpoints.py      # REST API endpoints (FastAPI routes)
├── database/
│   ├── connection.py     # Database connection manager (asyncpg)
│   └── models.py         # SQLAlchemy ORM models
├── integration/
│   └── design_agent_loader.py  # Design Agent integration
├── langgraph/
│   ├── nodes/            # LangGraph node implementations
│   │   ├── analysis_nodes.py       # Completeness analysis, gap identification
│   │   ├── code_analysis_nodes.py  # Code parsing, API inference (Week 9 enhanced)
│   │   ├── generation_nodes.py     # TRD/API/DB/Arch generation (Week 8 enhanced)
│   │   ├── load_inputs.py          # Load PRD and design docs
│   │   ├── persistence_nodes.py    # Save documents to DB
│   │   ├── research_nodes.py       # Technology research, user decisions
│   │   └── __init__.py
│   ├── checkpointer.py   # LangGraph checkpoint storage
│   ├── error_logging.py  # Error persistence to agent_error_logs
│   ├── state.py          # TechSpecState schema definition
│   ├── workflow.py       # LangGraph workflow definition (19 nodes)
│   └── __init__.py
├── llm/
│   └── client.py         # LLM client wrapper (Anthropic Claude)
├── research/
│   └── web_search.py     # Tavily web search integration
├── websocket/
│   └── connection_manager.py  # WebSocket connection manager
├── config.py             # Configuration management (pydantic-settings)
├── main.py               # FastAPI application entry point
└── __init__.py
```

## Tests (`tests/`)
```
tests/
├── integration/          # Integration tests
│   ├── test_api_integration.py        # API endpoint tests
│   ├── test_database_integration.py   # Database operation tests
│   ├── test_workflow_integration.py   # Full workflow tests
│   └── __init__.py
├── performance/          # Performance tests
│   ├── conftest.py                    # Performance test fixtures
│   ├── test_cross_schema_performance.py
│   ├── test_query_performance.py
│   └── __init__.py
├── unit/                 # Unit tests
│   ├── test_api_endpoints.py         # API endpoint unit tests
│   ├── test_config.py                # Configuration tests
│   ├── test_database.py              # Database unit tests
│   ├── test_design_agent_loader.py   # Integration loader tests
│   ├── test_error_logging.py         # Error logging tests
│   ├── test_main.py                  # Main app tests
│   ├── test_models.py                # ORM model tests
│   ├── test_state.py                 # State schema tests
│   ├── test_workflow_nodes.py        # LangGraph node tests
│   └── __init__.py
├── conftest.py           # Pytest fixtures and configuration
└── __init__.py
```

## Key Configuration Files

### pyproject.toml
- **Purpose**: Python project metadata and dependencies
- **Sections**:
  - `[project]`: Name, version, dependencies
  - `[project.optional-dependencies]`: Dev dependencies
  - `[tool.pytest.ini_options]`: Pytest configuration
  - `[tool.black]`: Black formatter settings
  - `[tool.ruff]`: Ruff linter settings
  - `[tool.mypy]`: Type checker settings
  - `[tool.isort]`: Import sorter settings

### .env.example
- **Purpose**: Template for environment variables
- **Sections**:
  - Database configuration (PostgreSQL)
  - LLM API keys (Anthropic, OpenAI, Tavily)
  - Redis cache settings
  - Tech Spec Agent configuration
  - ANYON platform integration
  - Security (JWT, CORS)
  - Monitoring & logging
  - Feature flags

### alembic.ini
- **Purpose**: Alembic database migration configuration
- **Key Settings**: Database URL, migration script location

### docker-compose.yml
- **Services**:
  - PostgreSQL (port 5432)
  - Redis (port 6379)
  - Tech Spec Agent API (port 8000)
  - Prometheus (port 9090)
  - Grafana (port 3001)

## Important Files by Functionality

### LangGraph Workflow
- **Entry Point**: `src/langgraph/workflow.py` - 19-node workflow definition
- **State**: `src/langgraph/state.py` - TechSpecState TypedDict
- **Nodes**: `src/langgraph/nodes/*.py` - Individual node implementations

### Week 8 Enhancements (TRD Quality)
- **File**: `src/langgraph/nodes/generation_nodes.py`
- **Lines 562-808**: Few-shot examples for TRD generation
- **Lines 720-818**: Structured format validation
- **Lines 532-718**: Multi-agent TRD review system

### Week 9 Enhancements (API Inference)
- **File**: `src/langgraph/nodes/code_analysis_nodes.py`
- **Lines 488-671**: AST-like parsing (TypeScript interface, function calls, imports, hooks)
- **Lines 674-792**: GraphQL support (detection, extraction, operations)
- **Lines 797-877**: Enhanced component parsing
- **Lines 377-429**: Fixed _extract_api_calls (actually uses enhanced functions)
- **Lines 215-227**: Fixed state writes (uses "inferred_apis" field)

### Database Models
- **File**: `src/database/models.py`
- **Tables**: tech_spec_sessions, tech_research, tech_conversations, generated_trd_documents

### API Endpoints
- **File**: `src/api/endpoints.py`
- **Routes**: `/api/projects/{id}/start-tech-spec`, `/api/tech-spec/sessions/{id}/status`, etc.
