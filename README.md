# Tech Spec Agent

**Technical Specification Agent for ANYON Platform** - Automated TRD Generation

[![CI/CD](https://github.com/anyon/tech-spec-agent/workflows/CI%2FCD/badge.svg)](https://github.com/anyon/tech-spec-agent/actions)
[![codecov](https://codecov.io/gh/anyon/tech-spec-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/anyon/tech-spec-agent)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The Tech Spec Agent is an AI-powered system that automatically generates Technical Requirements Documents (TRDs), API specifications, database schemas, and architecture diagrams from Product Requirements Documents (PRDs) and design outputs.

### Key Features

- **Automated TRD Generation**: Generate comprehensive technical specifications from PRDs
- **Technology Research**: AI-powered research and recommendations for open-source libraries
- **Interactive Decision-Making**: Real-time WebSocket communication for user technology selections
- **Code Analysis**: Parse Google AI Studio code to infer API specifications
- **Document Generation**: TRD, API specs (OpenAPI), DB schemas (SQL DDL), architecture diagrams (Mermaid)
- **Quality Validation**: 90% quality threshold with iterative refinement
- **Design Agent Integration**: Seamless integration via shared PostgreSQL tables
- **Production-Ready**: Monitoring, error recovery, and high availability

---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ANYON Platform                          │
│  (Frontend: TechSpecChat Component + Kanban Board)         │
└────────┬─────────────────────────────┬────────────────────┘
         │ REST API                    │ WebSocket
         ▼                             ▼
┌────────────────────────────────────────────────────────────┐
│              Tech Spec Agent (FastAPI)                      │
│  ┌──────────────────────────────────────────────────┐     │
│  │         LangGraph Workflow (17 Nodes)            │     │
│  └──────────────────────────────────────────────────┘     │
└────────┬──────────────────────────┬───────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐
│  PostgreSQL DB      │    │  Redis Cache        │
│  • shared.* tables  │    │  • Tech research    │
│  • tech_spec.*      │    │  • Parsed code      │
│  • agent_error_logs │    │                     │
└─────────────────────┘    └─────────────────────┘
```

### Technology Stack

- **Framework**: FastAPI 0.121+
- **Workflow Engine**: LangGraph 1.0.3+
- **LLM**: Claude Sonnet 4 (via Anthropic API)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 5.2+
- **Monitoring**: Prometheus + Grafana
- **Deployment**: Docker + docker-compose

---

## Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Redis**: 5.2 or higher
- **Docker**: 20.10+ (optional, for containerized development)
- **API Keys**:
  - Anthropic API Key (Claude)
  - OpenAI API Key (Google AI Studio integration)
  - Tavily API Key (web search)

---

## Installation

### Option 1: Local Development (Without Docker)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/anyon/tech-spec-agent.git
   cd tech-spec-agent
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

4. **Install development dependencies** (for testing):
   ```bash
   pip install -e ".[dev]"
   ```

5. **Install PostgreSQL and Redis**:
   - **PostgreSQL**: Download from https://www.postgresql.org/download/
   - **Redis**: Download from https://redis.io/download/ or use Docker:
     ```bash
     docker run -d -p 6379:6379 redis:7-alpine
     ```

### Option 2: Docker Development (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/anyon/tech-spec-agent.git
   cd tech-spec-agent
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - Tech Spec Agent API (port 8000)
   - Prometheus (port 9090)
   - Grafana (port 3001)

---

## Configuration

### Environment Variables

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and set your values**:
   ```bash
   # Required - Database
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/anyon_db
   DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/anyon_db

   # Required - LLM APIs
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   OPENAI_API_KEY=sk-your-key-here
   TAVILY_API_KEY=tvly-your-key-here

   # Required - ANYON Integration
   ANYON_API_BASE_URL=https://anyon.platform/api
   ANYON_WEBHOOK_SECRET=your-webhook-secret
   ANYON_FRONTEND_URL=https://anyon.platform

   # Required - Security
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

   # Optional - See .env.example for all options
   ```

### Database Setup

1. **Create database** (if not using Docker):
   ```bash
   createdb anyon_db
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Verify database connection**:
   ```bash
   python -c "from src.database.connection import db_manager; import asyncio; asyncio.run(db_manager.check_connection())"
   ```

---

## Running the Application

### Local Development

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f tech-spec-agent

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -t tech-spec-agent:latest .

# Run production container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  tech-spec-agent:latest
```

---

## Development

### Project Structure

```
Tech Agent/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration management
│   ├── database/
│   │   ├── connection.py          # Database connection manager
│   │   └── models.py              # SQLAlchemy models
│   ├── api/
│   │   └── endpoints.py           # REST API endpoints
│   ├── langgraph/
│   │   ├── state.py               # State schema
│   │   ├── workflow.py            # Workflow definition
│   │   └── nodes/                 # Individual node implementations
│   ├── integration/
│   │   └── design_agent_loader.py # Design Agent integration
│   └── websocket/
│       └── connection_manager.py  # WebSocket manager
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── alembic/                       # Database migrations
├── monitoring/                    # Prometheus & Grafana configs
├── .github/workflows/             # CI/CD pipelines
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type check with mypy
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks:

```bash
pip install pre-commit
pre-commit install
```

---

## Testing

### Run All Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_config.py -v

# Run with specific marker
pytest -m "slow" -v
```

### Test Coverage

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open coverage report
# Linux/Mac: open htmlcov/index.html
# Windows: start htmlcov/index.html
```

**Coverage Target**: 80%+

---

## Deployment

### Docker Deployment

1. **Build image**:
   ```bash
   docker build -t anyon/tech-spec-agent:1.0.0 .
   ```

2. **Push to registry**:
   ```bash
   docker push anyon/tech-spec-agent:1.0.0
   ```

3. **Deploy to server**:
   ```bash
   docker pull anyon/tech-spec-agent:1.0.0
   docker run -d \
     -p 8000:8000 \
     --env-file .env \
     --name tech-spec-agent \
     anyon/tech-spec-agent:1.0.0
   ```

### Environment-Specific Configuration

- **Development**: `ENVIRONMENT=development` (enables debug, docs, reload)
- **Staging**: `ENVIRONMENT=staging` (limited debug, full logging)
- **Production**: `ENVIRONMENT=production` (no debug, no docs, optimized)

---

## API Documentation

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check endpoint |
| GET | `/` | API information |
| POST | `/api/projects/{project_id}/start-tech-spec` | Start Tech Spec session |
| GET | `/api/tech-spec/sessions/{session_id}/status` | Get session status |
| POST | `/api/tech-spec/sessions/{session_id}/decisions` | Submit user decision |
| GET | `/api/tech-spec/sessions/{session_id}/trd` | Download TRD |

### WebSocket Endpoint

- **URL**: `wss://api.anyon.platform/ws/tech-spec/{session_id}?token={jwt_token}`
- **Protocol**: Bidirectional JSON messages
- **Use Case**: Real-time progress updates and user interaction

**Full API documentation**: http://localhost:8000/docs (when running locally)

---

## Monitoring

### Prometheus Metrics

Access Prometheus at http://localhost:9090

**Key Metrics**:
- `tech_spec_sessions_total` - Total sessions created
- `tech_spec_session_duration_seconds` - Session duration histogram
- `tech_spec_trd_quality_score` - TRD quality score gauge
- `tech_spec_errors_total` - Total errors by type

### Grafana Dashboards

Access Grafana at http://localhost:3001 (default login: admin/admin)

**Pre-configured Dashboards**:
1. Session Overview - Active, paused, completed sessions
2. Performance Metrics - Response times, throughput
3. Error Rates - Error trends by node
4. Technology Popularity - Most selected technologies

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Test connection from Python
python -c "from src.database.connection import db_manager; import asyncio; asyncio.run(db_manager.check_connection())"
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# Test from Python
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"
```

### API Not Starting

```bash
# Check logs
docker-compose logs tech-spec-agent

# Check environment variables
env | grep DATABASE_URL

# Verify port is free
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

### Common Issues

1. **"Database connection failed"**: Check DATABASE_URL is correct and PostgreSQL is running
2. **"Redis connection failed"**: Check REDIS_URL and Redis service status
3. **"Invalid API key"**: Verify ANTHROPIC_API_KEY and OPENAI_API_KEY are set correctly
4. **"Health check failing"**: Check all services (PostgreSQL, Redis) are healthy

---

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `pytest`
5. **Check code quality**: `black src/ && ruff check src/ && mypy src/`
6. **Commit your changes**: `git commit -m "Add amazing feature"`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Standards

- **Python Version**: 3.11+
- **Code Style**: Black (line length 100)
- **Type Hints**: Required for all functions
- **Test Coverage**: Minimum 80%
- **Documentation**: Docstrings for all public functions

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: https://docs.anyon.platform/tech-spec-agent
- **Issues**: https://github.com/anyon/tech-spec-agent/issues
- **Email**: support@anyon.platform

---

## Acknowledgments

- **Design Agent** - For providing the architectural patterns
- **LangChain/LangGraph** - For workflow orchestration
- **Anthropic** - For Claude Sonnet 4 LLM
- **FastAPI** - For the excellent web framework

---

**Built with ❤️ by the ANYON Team**
