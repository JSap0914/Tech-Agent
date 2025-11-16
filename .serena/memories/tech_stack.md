# Technology Stack

## Backend (Python)
- **Python Version**: 3.11+ (currently using 3.13.7)
- **Web Framework**: FastAPI 0.121+ (async web framework)
- **Server**: Uvicorn with standard extras (ASGI server)
- **Workflow Engine**: LangGraph 1.0.3+ (state machine orchestration)
- **LangChain**: langchain, langchain-anthropic, langchain-openai, langchain-community

## AI/LLM
- **Primary LLM**: Claude Sonnet 4 (claude-sonnet-4-20250514) via Anthropic API 0.40+
- **Secondary**: OpenAI API 1.58+ (for Google AI Studio integration)
- **Web Search**: Tavily API 0.5+ (technology research)

## Database & Caching
- **Database**: PostgreSQL 15+ with asyncpg 0.30+ (async driver)
- **ORM**: SQLAlchemy 2.0.36+ (async support)
- **Migrations**: Alembic 1.14+
- **Synchronous Driver**: psycopg2-binary 2.9.10+ (for migrations)
- **Cache**: Redis 5.2+ with hiredis 2.3+ (C parser for performance)

## HTTP & Web
- **HTTP Client**: httpx 0.28+ (async), aiohttp 3.9+
- **WebSocket**: websockets 12.0+
- **File I/O**: aiofiles 23.2+ (async file operations)

## Code Parsing
- **AST Parsing**: tree-sitter 0.22+, tree-sitter-typescript 0.21+
- **HTML Parsing**: beautifulsoup4 4.12.3+

## Diagrams & Documentation
- **Diagram Generation**: diagrams 0.24+ (architecture diagrams)

## Configuration & Validation
- **Settings**: pydantic 2.10+, pydantic-settings 2.7+
- **Environment**: python-dotenv 1.0.1+

## Logging & Monitoring
- **Structured Logging**: structlog 24.4+
- **Metrics**: prometheus-client 0.20+
- **Monitoring Stack**: Prometheus + Grafana (ports 9090, 3001)
- **LLM Tracing**: LangSmith (optional)

## Security
- **JWT**: pyjwt[crypto] 2.9+, python-jose[cryptography] 3.3+
- **Password Hashing**: passlib[bcrypt] 1.7.4+

## Development Tools
- **Testing**: pytest 8.3+, pytest-asyncio 0.24+, pytest-cov 6.0+, pytest-mock 3.14+, pytest-timeout 2.3+
- **Type Checking**: mypy 1.13+ with types-redis, types-aiofiles
- **Linting**: ruff 0.8+ (fast Python linter)
- **Formatting**: black 24.10+ (line length 100), isort 5.13+
- **Debugging**: ipython 8.20+, ipdb 0.13.13+

## Deployment
- **Containerization**: Docker 20.10+, docker-compose
- **Platform**: Linux/Windows (currently on Windows MINGW64_NT-10.0-26200)

## Build System
- **Build Backend**: setuptools 68.0+, wheel
- **Package Name**: anyon-tech-spec-agent 1.0.0
