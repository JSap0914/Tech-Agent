# Suggested Commands for Development

## Setup Commands

### Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Database Setup
```bash
# Create database (if not using Docker)
createdb anyon_db

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "migration_name"

# Downgrade one revision
alembic downgrade -1

# Check database connection
python -c "from src.database.connection import db_manager; import asyncio; asyncio.run(db_manager.check_connection())"
```

## Running the Application

### Local Development
```bash
# Run FastAPI server with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
start http://localhost:8000/docs  # Windows
# or
open http://localhost:8000/docs   # Mac
```

### Docker Development
```bash
# Start all services (PostgreSQL, Redis, API, Prometheus, Grafana)
docker-compose up -d

# View logs
docker-compose logs -f tech-spec-agent

# Stop services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

## Code Quality Commands

### Formatting
```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Run both
black src/ tests/ && isort src/ tests/
```

### Linting
```bash
# Lint with Ruff
ruff check src/ tests/

# Lint and auto-fix
ruff check src/ tests/ --fix
```

### Type Checking
```bash
# Type check with mypy
mypy src/
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Testing Commands

### Run Tests
```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_config.py -v

# Run tests with specific marker
pytest -m "slow" -v

# Run tests in parallel (faster)
pytest -n auto

# Run with verbose output
pytest -vv
```

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open coverage report (Windows)
start htmlcov/index.html

# Open coverage report (Mac)
open htmlcov/index.html
```

## Monitoring Commands

### Redis
```bash
# Check Redis status
redis-cli ping

# Test Redis from Python
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"

# Start Redis with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### PostgreSQL
```bash
# Check PostgreSQL connection
psql -U postgres -c "SELECT 1"

# Connect to database
psql -U postgres -d anyon_db

# List databases
psql -U postgres -l
```

### Prometheus & Grafana
```bash
# Access Prometheus
start http://localhost:9090

# Access Grafana (default: admin/admin)
start http://localhost:3001
```

## Git Commands (Windows)
```bash
# Check git version
git --version

# Clone repository
git clone https://github.com/anyon/tech-spec-agent.git

# Create feature branch
git checkout -b feature/amazing-feature

# Stage changes
git add .

# Commit changes
git commit -m "Add amazing feature"

# Push to remote
git push origin feature/amazing-feature

# Pull latest changes
git pull origin main
```

## Windows System Commands
```bash
# List files
ls
# or
dir

# Change directory
cd "path\to\directory"

# Find process using port
netstat -ano | findstr :8000

# Kill process by PID
taskkill /PID <process_id> /F

# Check environment variables
echo %DATABASE_URL%
# or
set | findstr DATABASE_URL

# View Python path
where python

# View pip path
where pip
```

## Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Check API info
curl http://localhost:8000/

# Test WebSocket (requires wscat)
wscat -c ws://localhost:8000/ws/tech-spec/{session_id}?token={jwt_token}
```

## Deployment Commands

### Docker Production
```bash
# Build production image
docker build -t anyon/tech-spec-agent:1.0.0 .

# Push to registry
docker push anyon/tech-spec-agent:1.0.0

# Run production container
docker run -d -p 8000:8000 --env-file .env --name tech-spec-agent anyon/tech-spec-agent:1.0.0
```

## Troubleshooting Commands
```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check specific package version
pip show fastapi

# Reinstall package
pip install --force-reinstall package-name

# Clear pip cache
pip cache purge

# Check disk space
df -h  # Linux/Mac
# or
wmic logicaldisk get size,freespace,caption  # Windows
```
