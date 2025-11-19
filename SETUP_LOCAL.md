# Local Development Setup Guide (Without Docker)

This guide walks you through setting up the Tech Spec Agent for local development on Windows without Docker.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Install PostgreSQL](#step-1-install-postgresql)
- [Step 2: Install Redis](#step-2-install-redis)
- [Step 3: Install Python Dependencies](#step-3-install-python-dependencies)
- [Step 4: Configure Environment](#step-4-configure-environment)
- [Step 5: Initialize Database](#step-5-initialize-database)
- [Step 6: Start the Application](#step-6-start-the-application)
- [Troubleshooting](#troubleshooting)
- [Verification Checklist](#verification-checklist)

---

## Prerequisites

- **Windows 10/11** (MINGW64/Git Bash environment)
- **Python 3.11+** (verify with `python --version`)
- **Git** (for cloning repository)
- **Admin access** (for installing PostgreSQL/Redis)

---

## Step 1: Install PostgreSQL

### Option A: Using Official Installer (Recommended)

1. **Download PostgreSQL 15 or 16**:
   - Go to: https://www.postgresql.org/download/windows/
   - Download the Windows installer (e.g., `postgresql-15.x-windows-x64.exe`)

2. **Run the installer**:
   - Launch the installer as Administrator
   - Click "Next" through welcome screens
   - Installation directory: Default (`C:\Program Files\PostgreSQL\15`)
   - Select components: **Check all** (PostgreSQL Server, pgAdmin, Command Line Tools)
   - Data directory: Default (`C:\Program Files\PostgreSQL\15\data`)
   - **Password**: Enter `anyon_password_2025` (must match `.env` file)
   - Port: `5432` (default)
   - Locale: Default
   - Click "Next" and wait for installation to complete

3. **Add PostgreSQL to PATH** (if not done automatically):
   ```bash
   # Add to System Environment Variables:
   C:\Program Files\PostgreSQL\15\bin
   ```

4. **Verify installation**:
   ```bash
   # Open new terminal (to reload PATH)
   psql --version
   # Should output: psql (PostgreSQL) 15.x
   ```

### Step 2: Create Database and User

1. **Open PostgreSQL SQL Shell (psql)**:
   - Search for "SQL Shell (psql)" in Windows Start Menu
   - Press Enter for all default prompts (Server, Database, Port, Username)
   - Enter password: `anyon_password_2025` (or whatever you set during install)

2. **Create ANYON user and database**:
   ```sql
   -- Create user
   CREATE USER anyon_user WITH PASSWORD 'anyon_password_2025';

   -- Create database
   CREATE DATABASE anyon_db OWNER anyon_user;

   -- Grant privileges
   GRANT ALL PRIVILEGES ON DATABASE anyon_db TO anyon_user;

   -- Verify
   \l  -- List databases (should see anyon_db)
   \q  -- Quit
   ```

3. **Test connection**:
   ```bash
   psql -U anyon_user -d anyon_db -h localhost
   # Enter password: anyon_password_2025
   # Should connect successfully
   # Type \q to exit
   ```

---

## Step 2: Install Redis

### Option A: Using Windows Subsystem for Linux (WSL) - Recommended

1. **Install WSL** (if not already installed):
   ```bash
   # Open PowerShell as Administrator
   wsl --install
   # Restart computer if prompted
   ```

2. **Start WSL and install Redis**:
   ```bash
   # Open WSL terminal (search "Ubuntu" in Start Menu)
   sudo apt-get update
   sudo apt-get install redis-server -y
   ```

3. **Start Redis server**:
   ```bash
   # Start Redis in background
   sudo service redis-server start

   # Verify it's running
   redis-cli ping
   # Should return: PONG
   ```

4. **Auto-start Redis on Windows boot** (optional):
   ```bash
   # Add to ~/.bashrc
   echo "sudo service redis-server start" >> ~/.bashrc
   ```

### Option B: Using Native Windows Port (Alternative)

1. **Download Redis for Windows**:
   - Go to: https://github.com/microsoftarchive/redis/releases
   - Download `Redis-x64-3.2.100.zip` or latest version

2. **Extract and run**:
   ```bash
   # Extract to C:\Redis\
   # Open Command Prompt in C:\Redis\
   redis-server.exe
   ```

3. **Test connection**:
   ```bash
   # Open another Command Prompt
   redis-cli.exe ping
   # Should return: PONG
   ```

4. **Install as Windows Service** (optional):
   ```bash
   redis-server --service-install
   redis-server --service-start
   ```

---

## Step 3: Install Python Dependencies

1. **Clone the repository** (if not done already):
   ```bash
   cd "C:\Users\Han\Documents\SKKU 1st Grade\"
   git clone <repository-url> "Tech Agent"
   cd "Tech Agent"
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   ```bash
   # Git Bash / MINGW64
   source venv/Scripts/activate

   # Command Prompt
   venv\Scripts\activate.bat

   # PowerShell
   venv\Scripts\Activate.ps1
   ```

4. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

5. **Install dependencies**:
   ```bash
   pip install -e .
   ```

6. **Install development dependencies** (for testing):
   ```bash
   pip install -e ".[dev]"
   ```

---

## Step 4: Configure Environment

1. **Check .env file exists**:
   ```bash
   ls .env
   # Should exist and contain configuration
   ```

2. **Verify database connection strings** (should already be correct):
   ```bash
   # Open .env in text editor and verify:
   DATABASE_URL=postgresql+asyncpg://anyon_user:anyon_password_2025@localhost:5432/anyon_db
   DATABASE_URL_SYNC=postgresql://anyon_user:anyon_password_2025@localhost:5432/anyon_db
   REDIS_URL=redis://localhost:6379/0
   ```

3. **Set API keys** (if not already set):
   ```bash
   # Edit .env and add your API keys:
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   TAVILY_API_KEY=tvly-your-key-here
   OPENAI_API_KEY=sk-your-key-here  # Optional, for Google AI Studio integration
   ```

---

## Step 5: Initialize Database

1. **Run database migrations**:
   ```bash
   # Make sure virtual environment is activated
   alembic upgrade head
   ```

2. **Verify database schema**:
   ```bash
   # Connect to database
   psql -U anyon_user -d anyon_db -h localhost

   # List tables
   \dt
   # Should see: tech_spec_sessions, tech_research, tech_conversations, generated_trd_documents, etc.

   # Exit
   \q
   ```

3. **Test database connection from Python**:
   ```bash
   python -c "from src.database.connection import db_manager; import asyncio; asyncio.run(db_manager.check_connection())"
   # Should output: Database connection successful
   ```

---

## Step 6: Start the Application

### Option A: Using Batch File (Easiest)

```bash
# Double-click on:
start_tech_spec_agent.bat

# Or run from terminal:
./start_tech_spec_agent.bat
```

### Option B: Using Uvicorn Directly

```bash
# Activate virtual environment first
source venv/Scripts/activate

# Start the server
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Verify Application is Running

1. **Check health endpoint**:
   ```bash
   curl http://localhost:8001/health
   # Should return: {"status": "healthy", ...}
   ```

2. **Check API documentation**:
   - Open browser to: http://localhost:8001/docs
   - Should see FastAPI Swagger UI with all endpoints

3. **Check main endpoint**:
   ```bash
   curl http://localhost:8001/
   # Should return API information
   ```

---

## Troubleshooting

### PostgreSQL Issues

#### Error: "psql: command not found"
**Solution**: Add PostgreSQL to PATH
```bash
# Add to System Environment Variables:
C:\Program Files\PostgreSQL\15\bin
# Restart terminal
```

#### Error: "password authentication failed"
**Solution**: Check password in .env matches PostgreSQL user password
```bash
# Reset PostgreSQL password:
psql -U postgres
ALTER USER anyon_user WITH PASSWORD 'anyon_password_2025';
\q
```

#### Error: "database 'anyon_db' does not exist"
**Solution**: Create the database
```bash
psql -U postgres
CREATE DATABASE anyon_db OWNER anyon_user;
\q
```

#### Error: "could not connect to server: Connection refused"
**Solution**: Start PostgreSQL service
```bash
# Windows Services
services.msc
# Find "postgresql-x64-15" and click Start

# Or via command line (as Administrator)
net start postgresql-x64-15
```

### Redis Issues

#### Error: "redis-cli: command not found"
**Solution**: Install Redis (see Step 2)

#### Error: "Could not connect to Redis at 127.0.0.1:6379"
**Solution**: Start Redis server
```bash
# WSL
sudo service redis-server start

# Windows native
redis-server.exe

# Or as service
net start Redis
```

#### Error: "Connection refused"
**Solution**: Check Redis is running on port 6379
```bash
# WSL
sudo service redis-server status

# Windows
netstat -ano | findstr :6379
```

### Python/Application Issues

#### Error: "No module named 'src'"
**Solution**: Install package in editable mode
```bash
pip install -e .
```

#### Error: "alembic: command not found"
**Solution**: Install alembic
```bash
pip install alembic
```

#### Error: "ModuleNotFoundError: No module named 'XXX'"
**Solution**: Install missing dependency
```bash
pip install -e ".[dev]"
```

#### Error: "Port 8001 already in use"
**Solution**: Kill existing process or use different port
```bash
# Find process using port 8001
netstat -ano | findstr :8001

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in .env
API_PORT=8002
```

### Database Migration Issues

#### Error: "Can't locate revision identified by 'XXXX'"
**Solution**: Reset migrations
```bash
# Drop all tables
psql -U anyon_user -d anyon_db
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q

# Re-run migrations
alembic upgrade head
```

### Performance Issues

#### Slow startup time
**Possible causes**:
- Database connection timeout - check PostgreSQL is running
- Redis connection timeout - check Redis is running
- Missing dependencies - run `pip install -e .`

#### High memory usage
**Solution**: Reduce connection pool sizes in .env
```bash
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
REDIS_MAX_CONNECTIONS=25
```

---

## Verification Checklist

After setup, verify everything is working:

- [ ] PostgreSQL service is running
- [ ] Redis service is running
- [ ] Database `anyon_db` exists with user `anyon_user`
- [ ] All database tables created (via Alembic migrations)
- [ ] Python virtual environment activated
- [ ] All dependencies installed
- [ ] Environment variables configured (.env file)
- [ ] Application starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] API docs accessible at http://localhost:8001/docs
- [ ] Database connection successful
- [ ] Redis connection successful
- [ ] Integration tests pass

**Run this command to verify everything**:
```bash
# Start services
sudo service redis-server start  # WSL
# Or: redis-server.exe           # Windows

# Test database
psql -U anyon_user -d anyon_db -h localhost -c "SELECT 1;"

# Test Redis
redis-cli ping

# Start application
./start_tech_spec_agent.bat

# In another terminal, test health
curl http://localhost:8001/health

# Run tests
pytest tests/integration/test_architecture_generation.py -v
```

---

## Daily Development Workflow

```bash
# 1. Start services (do once per day)
sudo service redis-server start  # WSL
# PostgreSQL usually starts automatically

# 2. Activate virtual environment
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
source venv/Scripts/activate

# 3. Start application
./start_tech_spec_agent.bat

# 4. Develop and test
# ... make changes ...
pytest tests/ -v

# 5. Stop application (Ctrl+C)
```

---

## Additional Resources

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Redis Documentation**: https://redis.io/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/

---

## Questions?

If you encounter issues not covered in this guide:

1. Check application logs for detailed error messages
2. Verify all services are running (`psql`, `redis-cli ping`)
3. Ensure .env configuration matches your setup
4. Try the troubleshooting steps above
5. Check README.md for additional information

---

**Last Updated**: 2025-01-16
**Version**: 1.0 (Docker-free setup)
