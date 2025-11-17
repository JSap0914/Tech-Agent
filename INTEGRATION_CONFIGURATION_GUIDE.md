# Tech Spec Agent ↔ Design Agent Integration Configuration Guide

**Last Updated**: 2025-01-16
**Status**: Ready for Integration
**Configuration Complexity**: Medium

---

## 🎯 Executive Summary

This guide provides **step-by-step instructions** to configure and connect:
- **Tech Spec Agent** (`C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent`)
- **Design Agent** (`C:\Users\Han\Documents\SKKU 1st Grade\Design Agent`)

Both agents share a PostgreSQL database and communicate through the `shared` schema.

---

## ⚠️ **CRITICAL ISSUE FOUND: Database Schema Mismatch**

### Problem

**Tech Spec Agent expects**:
```sql
-- Foreign key in Tech Spec Agent migration (line 41)
FOREIGN KEY (design_job_id) REFERENCES shared.design_jobs(id)
```

**Design Agent has**:
```sql
-- Primary key in Design Agent migration
CREATE TABLE shared.design_jobs (
    job_id UUID PRIMARY KEY,  -- ❌ Column named 'job_id', not 'id'
    ...
)
```

### Impact

- ❌ Tech Spec Agent migrations will FAIL when trying to create foreign key
- ❌ Cannot join Tech Spec sessions to Design Agent jobs
- ❌ Integration will not work

### Fix Required

**Option 1: Fix Tech Spec Agent Migration (RECOMMENDED)**

Edit `Tech Agent/alembic/versions/001_initial_schema.py` line 41:

```python
# BEFORE (❌ WRONG):
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.id'], ondelete='CASCADE'),

# AFTER (✅ CORRECT):
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.job_id'], ondelete='CASCADE'),
```

**Option 2: Fix Design Agent Migration (NOT RECOMMENDED)**

If Design Agent hasn't been deployed yet, you could rename `job_id` → `id`, but this breaks consistency with Design Agent code.

---

## 📋 Prerequisites Checklist

Before starting configuration, ensure you have:

- [ ] **PostgreSQL 14+** installed and running
- [ ] **Redis 7+** installed and running
- [ ] **Python 3.11+** (Python 3.13 recommended)
- [ ] **Anthropic API Key** (for Claude Sonnet 4.5)
- [ ] **GitHub Token** (for open-source library search)
- [ ] **Google API Key + Search Engine ID** (for Design Agent web search)
- [ ] Both agent repositories cloned:
  - `C:\Users\Han\Documents\SKKU 1st Grade\Design Agent`
  - `C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent`

---

## 🗄️ Step 1: Database Setup

### 1.1 Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database
CREATE DATABASE anyon_db;

-- Create database user (if not exists)
CREATE USER anyon_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE anyon_db TO anyon_user;

-- Exit
\q
```

### 1.2 Create Schemas

```sql
-- Connect to anyon_db
psql -U anyon_user -d anyon_db

-- Create schemas
CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS design_agent;
CREATE SCHEMA IF NOT EXISTS tech_spec;

-- Grant schema usage
GRANT USAGE ON SCHEMA shared TO anyon_user;
GRANT USAGE ON SCHEMA design_agent TO anyon_user;
GRANT USAGE ON SCHEMA tech_spec TO anyon_user;

-- Grant create privileges
GRANT CREATE ON SCHEMA shared TO anyon_user;
GRANT CREATE ON SCHEMA design_agent TO anyon_user;
GRANT CREATE ON SCHEMA tech_spec TO anyon_user;

-- Exit
\q
```

### 1.3 Database Connection Strings

Both agents should use the **same database** with **different schemas**:

```bash
# Shared connection string
DATABASE_URL=postgresql+asyncpg://anyon_user:your_secure_password@localhost:5432/anyon_db
DATABASE_SYNC_URL=postgresql://anyon_user:your_secure_password@localhost:5432/anyon_db
```

---

## 🔧 Step 2: Fix Tech Spec Agent Migration (CRITICAL)

### 2.1 Fix Foreign Key Reference

**File**: `Tech Agent/alembic/versions/001_initial_schema.py`

```python
# Line 41 - CHANGE THIS:
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.id'], ondelete='CASCADE'),

# TO THIS:
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.job_id'], ondelete='CASCADE'),
```

### 2.2 Verify the Fix

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Check the migration file
grep "shared.design_jobs" alembic/versions/001_initial_schema.py
```

**Expected output**:
```
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.job_id'], ondelete='CASCADE'),
```

---

## 🔧 Step 3: Update Tech Spec Agent Integration Code

### 3.1 Fix Design Agent Loader

**File**: `Tech Agent/src/database/models.py`

The models already reference the correct column names, but verify:

```python
# Line 90-94 should look like this:
design_job_id = Column(
    UUID(as_uuid=True),
    ForeignKey("shared.design_jobs.job_id", ondelete="CASCADE"),  # ✅ Correct
    nullable=False,
    index=True,
)
```

**File**: `Tech Agent/src/integration/design_agent_loader.py`

Verify queries use correct column name:

```python
# Should already be correct, but verify:
query = select(DesignOutput).where(DesignOutput.design_job_id == design_job_id)
```

---

## ⚙️ Step 4: Configure Design Agent Environment

### 4.1 Create .env File

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
cp .env.example .env
```

### 4.2 Edit Design Agent .env

**File**: `Design Agent/.env`

```bash
# Application
APP_NAME=ANYON Design Agent
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database - SHARED WITH TECH SPEC AGENT
DATABASE_URL=postgresql+asyncpg://anyon_user:your_secure_password@localhost:5432/anyon_db
DATABASE_SYNC_URL=postgresql://anyon_user:your_secure_password@localhost:5432/anyon_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# Redis - SHARED WITH TECH SPEC AGENT
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# LLM - Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-api03-your_actual_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7

# GitHub (for open-source library search)
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_API_URL=https://api.github.com

# Google Search (for web search)
GOOGLE_API_KEY=AIza_your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# LangGraph
LANGGRAPH_CHECKPOINT_SCHEMA=design_agent
LANGGRAPH_MAX_ITERATIONS=50

# Design Agent Configuration
MAX_SCREENS=12
MIN_SCREENS=3
QUALITY_SCORE_THRESHOLD=90

# Job Processing
JOB_POLL_INTERVAL=1.0
JOB_MAX_RETRIES=3
JOB_TIMEOUT=3600
PROGRESS_UPDATE_INTERVAL=5

# Document Generation
DOCUMENT_VERSION=0.9
PARALLEL_DOCUMENT_GENERATION=true

# Validation
ENABLE_TYPESCRIPT_VALIDATION=true
ENABLE_TAILWIND_VALIDATION=true
ENABLE_ACCESSIBILITY_VALIDATION=true
```

---

## ⚙️ Step 5: Configure Tech Spec Agent Environment

### 5.1 Create .env File

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Check if .env.example exists
ls .env.example
```

### 5.2 Create Tech Spec Agent .env

**File**: `Tech Agent/.env`

```bash
# Application
APP_NAME=ANYON Tech Spec Agent
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database - SHARED WITH DESIGN AGENT (SAME DATABASE!)
DATABASE_URL=postgresql+asyncpg://anyon_user:your_secure_password@localhost:5432/anyon_db
DATABASE_SYNC_URL=postgresql://anyon_user:your_secure_password@localhost:5432/anyon_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# Redis - SHARED WITH DESIGN AGENT (SAME REDIS!)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# LLM - Anthropic Claude (SAME API KEY AS DESIGN AGENT)
ANTHROPIC_API_KEY=sk-ant-api03-your_actual_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7

# Tavily Web Search (for technology research)
TAVILY_API_KEY=tvly-your_tavily_api_key_here
TAVILY_MAX_RESULTS=10

# Tech Spec Agent Configuration
TECH_SPEC_SESSION_TIMEOUT=3600
TECH_SPEC_MAX_RESEARCH_RETRIES=3
TECH_SPEC_WEB_SEARCH_TIMEOUT=30
TECH_SPEC_MIN_OPTIONS_PER_GAP=2
TECH_SPEC_MAX_OPTIONS_PER_GAP=3
TECH_SPEC_TRD_VALIDATION_THRESHOLD=90

# LangGraph Checkpointing
LANGGRAPH_CHECKPOINT_ENABLED=true
LANGGRAPH_MAX_ITERATIONS=50

# Caching
ENABLE_CACHING=true
CACHE_TTL=900

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001  # Different port from Design Agent!
API_RELOAD=true
API_CORS_ORIGINS=http://localhost:3000,https://anyon.platform

# WebSocket Configuration
ENABLE_WEBSOCKET=true
WEBSOCKET_BASE_URL=ws://localhost:8001/ws

# Monitoring
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9091  # Different from Design Agent!
ENABLE_LANGSMITH=false

# Security
SECRET_KEY=your_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

---

## 🗃️ Step 6: Run Database Migrations

### 6.1 Run Design Agent Migrations FIRST

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"

# Activate virtual environment
venv\Scripts\activate

# Run migrations to create shared schema
alembic upgrade head

# Verify shared tables created
psql -U anyon_user -d anyon_db -c "\dt shared.*"
```

**Expected output**:
```
              List of relations
 Schema |        Name           | Type  |   Owner
--------+-----------------------+-------+------------
 shared | design_decisions      | table | anyon_user
 shared | design_jobs           | table | anyon_user
 shared | design_outputs        | table | anyon_user
 shared | design_progress       | table | anyon_user
 shared | open_source_selections| table | anyon_user
```

### 6.2 Run Tech Spec Agent Migrations SECOND

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Activate virtual environment
venv\Scripts\activate

# Run migrations to create Tech Spec tables
alembic upgrade head

# Verify Tech Spec tables created
psql -U anyon_user -d anyon_db -c "\dt public.*"
```

**Expected output**:
```
              List of relations
 Schema |         Name             | Type  |   Owner
--------+--------------------------+-------+------------
 public | agent_error_logs         | table | anyon_user
 public | generated_trd_documents  | table | anyon_user
 public | tech_conversations       | table | anyon_user
 public | tech_research            | table | anyon_user
 public | tech_spec_sessions       | table | anyon_user
```

### 6.3 Verify Foreign Key Constraint

```sql
-- Check if foreign key exists
psql -U anyon_user -d anyon_db

SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE contype = 'f'
  AND conname LIKE '%design_job%';
```

**Expected output**:
```
          constraint_name           |      table_name      | referenced_table
------------------------------------+----------------------+------------------
 tech_spec_sessions_design_job_id_fkey | tech_spec_sessions   | design_jobs
```

✅ If you see this, the foreign key is working correctly!

---

## 🚀 Step 7: Start Both Agents

### 7.1 Start Design Agent

**Terminal 1**:
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
venv\Scripts\activate

# Start Redis (if not running)
redis-server

# Start Design Agent job listener
python -m src.workers.job_listener
```

**Expected output**:
```
INFO: Design Agent job listener started
INFO: Listening for new jobs on shared.design_jobs...
INFO: PostgreSQL LISTEN/NOTIFY configured
INFO: Worker ready to process design jobs
```

### 7.2 Start Tech Spec Agent

**Terminal 2**:
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
venv\Scripts\activate

# Start Tech Spec Agent API server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Expected output**:
```
INFO: Starting Tech Spec Agent
INFO: Database connection established
INFO: Redis cache client initialized successfully
INFO: LangGraph workflow initialized
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8001
```

### 7.3 Verify Health Checks

**Check Design Agent**:
```bash
# If Design Agent has a health endpoint
curl http://localhost:8000/health
```

**Check Tech Spec Agent**:
```bash
curl http://localhost:8001/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "service": "tech-spec-agent",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

---

## 🧪 Step 8: Test Integration

### 8.1 Create Test Design Job

**Insert test job into database**:

```sql
psql -U anyon_user -d anyon_db

-- Insert test Design Job
INSERT INTO shared.design_jobs (
    job_id,
    project_id,
    user_id,
    prd_content,
    trd_content,
    status
) VALUES (
    gen_random_uuid(),
    'test-project-001',
    'test-user-001',
    '# PRD Content

Create a task management web app with user authentication and real-time updates.',
    '# TRD Content

Technology Requirements:
- Frontend: React 18 with TypeScript
- Backend: Node.js with Express
- Database: To be decided by Tech Spec Agent
- Real-time: To be decided by Tech Spec Agent',
    'pending'
) RETURNING job_id;
```

**Save the returned `job_id` - you'll need it!**

### 8.2 Monitor Design Agent Progress

The Design Agent should automatically pick up the job. Monitor progress:

```sql
-- Check job status
SELECT job_id, status, created_at, started_at
FROM shared.design_jobs
WHERE project_id = 'test-project-001';

-- Check progress
SELECT current_phase, phase_name, progress_percent
FROM shared.design_progress
WHERE job_id = '<job_id_from_above>';
```

### 8.3 Wait for Design Agent to Complete

Design Agent will go through 6 phases (30-45 minutes total). Wait until:

```sql
SELECT status FROM shared.design_jobs WHERE job_id = '<job_id>';
-- Expected: 'completed'
```

### 8.4 Start Tech Spec Agent Session

Once Design Agent completes, trigger Tech Spec Agent via REST API:

```bash
# Replace <job_id> with actual Design Job ID
curl -X POST http://localhost:8001/api/projects/test-project-001/start-tech-spec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "design_job_id": "<job_id_from_design_agent>",
    "user_id": "test-user-001"
  }'
```

**Expected response**:
```json
{
  "session_id": "uuid-of-tech-spec-session",
  "project_id": "test-project-001",
  "status": "pending",
  "websocket_url": "ws://localhost:8001/ws/tech-spec/<session_id>",
  "created_at": "2025-01-16T10:00:00Z"
}
```

### 8.5 Monitor Tech Spec Agent via WebSocket

Connect to WebSocket to see real-time updates:

```javascript
// Example WebSocket client
const ws = new WebSocket('ws://localhost:8001/ws/tech-spec/<session_id>?token=<jwt_token>');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress + '%');
    console.log('Message:', data.message);
};
```

### 8.6 Verify Tech Spec Completion

Wait 15-25 minutes, then check:

```sql
-- Check Tech Spec session status
SELECT id, status, progress_percentage, current_stage
FROM tech_spec_sessions
WHERE design_job_id = '<design_job_id>';

-- Check generated TRD documents
SELECT
    session_id,
    quality_score,
    version,
    created_at
FROM generated_trd_documents
WHERE session_id = '<tech_spec_session_id>';
```

**Success criteria**:
- ✅ `tech_spec_sessions.status = 'completed'`
- ✅ `tech_spec_sessions.progress_percentage = 100.0`
- ✅ `generated_trd_documents.quality_score >= 90.0`

---

## 📊 Configuration Summary

### Shared Resources

| Resource | Value | Used By |
|----------|-------|---------|
| **PostgreSQL Database** | `anyon_db` | Both agents |
| **PostgreSQL User** | `anyon_user` | Both agents |
| **Redis Instance** | `localhost:6379/0` | Both agents |
| **Anthropic API Key** | Same key | Both agents |
| **Shared Schema** | `shared.*` tables | Both agents |

### Agent-Specific Resources

| Resource | Design Agent | Tech Spec Agent |
|----------|--------------|-----------------|
| **API Port** | 8000 | 8001 |
| **Prometheus Port** | 9090 | 9091 |
| **Database Schema** | `design_agent` | `public` |
| **LangGraph Checkpoint** | `design_agent.checkpoints` | `public.checkpoints` |
| **Job Listener** | PostgreSQL NOTIFY | N/A |
| **Web Search** | Google Custom Search | Tavily API |

---

## 🔍 Troubleshooting

### Issue 1: "Foreign key constraint violation"

**Symptom**: Tech Spec Agent migration fails with:
```
ERROR: relation "shared.design_jobs.id" does not exist
```

**Solution**: You didn't fix the migration! Go back to **Step 2** and change `id` → `job_id`.

---

### Issue 2: "shared schema does not exist"

**Symptom**: Tech Spec Agent migration fails:
```
ERROR: schema "shared" does not exist
```

**Solution**: Run Design Agent migrations FIRST (Step 6.1). Design Agent creates the `shared` schema.

---

### Issue 3: "Database connection failed"

**Symptom**: Either agent fails to start with database error.

**Solution**:
1. Verify PostgreSQL is running: `pg_ctl status`
2. Test connection: `psql -U anyon_user -d anyon_db`
3. Check `.env` DATABASE_URL is correct
4. Verify user has privileges (Step 1.2)

---

### Issue 4: "Redis connection failed"

**Symptom**: Agent starts but warns "Redis cache health check failed".

**Solution**:
1. Start Redis: `redis-server`
2. Verify Redis is running: `redis-cli ping` (should return `PONG`)
3. Check `.env` REDIS_URL is `redis://localhost:6379/0`

---

### Issue 5: "Design Job not found"

**Symptom**: Tech Spec Agent API returns 400 error.

**Solution**:
1. Verify Design Job exists: `SELECT * FROM shared.design_jobs WHERE job_id = '<id>';`
2. Verify Design Job status is `completed`
3. Check you're using the correct `job_id` (not `id`)

---

### Issue 6: "WebSocket authentication failed"

**Symptom**: WebSocket closes immediately with code 1008.

**Solution**:
1. Verify JWT token is valid and not expired
2. Check token is passed in query parameter: `?token=<jwt>`
3. Verify user owns the session

---

## 🎯 Quick Start Checklist

After configuration, verify everything is working:

- [ ] PostgreSQL running with `anyon_db` database
- [ ] Redis running on port 6379
- [ ] Design Agent migrations applied (created `shared` schema)
- [ ] Tech Spec Agent migrations applied (created Tech Spec tables)
- [ ] Foreign key `tech_spec_sessions.design_job_id → shared.design_jobs.job_id` exists
- [ ] Design Agent `.env` configured with all API keys
- [ ] Tech Spec Agent `.env` configured with all API keys
- [ ] Design Agent job listener running (Terminal 1)
- [ ] Tech Spec Agent API server running (Terminal 2)
- [ ] Health checks return `status: "healthy"` for both agents
- [ ] Test Design Job inserted and completed
- [ ] Test Tech Spec session created and completed
- [ ] Generated TRD documents exist with quality score >= 90

---

## 📞 Next Steps After Configuration

Once configuration is complete:

1. **Deploy to Staging**: Set up staging environment with same configuration
2. **Create ANYON Platform Integration**: Build Kanban board integration
3. **Build Frontend Components**: Create `TechSpecChat.tsx` for user interaction
4. **Set Up Monitoring**: Configure Grafana dashboards
5. **Load Testing**: Test with 50+ concurrent sessions
6. **Connect Backlog Agent**: Implement `notify_next_agent` event publishing

---

## 📚 Reference

### Configuration Files Modified

- `Design Agent/.env` - Design Agent environment variables
- `Tech Agent/.env` - Tech Spec Agent environment variables
- `Tech Agent/alembic/versions/001_initial_schema.py` - Fixed foreign key

### Database Tables Created

**Shared Schema** (by Design Agent):
- `shared.design_jobs`
- `shared.design_progress`
- `shared.design_outputs`
- `shared.design_decisions`
- `shared.open_source_selections`

**Tech Spec Schema** (by Tech Spec Agent):
- `tech_spec_sessions`
- `tech_research`
- `tech_conversations`
- `generated_trd_documents`
- `agent_error_logs`

### Architecture Documentation Outputs

Tech Spec Agent automatically generates **THREE types of architecture documentation**:

#### 1. System Architecture Text (TRD Section 3) - 70%
- **Location**: Within `trd_content` column as Section 3
- **Format**: Markdown text
- **Contents**:
  - Architecture pattern description (3-tier, microservices, etc.)
  - Component breakdown and responsibilities
  - Data flow between components
  - Integration points with third-party services
  - Scalability and fault tolerance strategies

#### 2. Database ERD (Mermaid) - 85%
- **Location**: `database_schema` JSONB column (ERD + SQL DDL)
- **Format**: Mermaid Entity Relationship Diagram + SQL statements
- **Contents**:
  - Entity relationships
  - Foreign keys
  - Primary keys
  - Table structure

#### 3. System Architecture Diagram (Mermaid) - 90%
- **Location**: `architecture_diagram` TEXT column
- **Format**: Mermaid flowchart
- **Contents**:
  - Client applications (web, mobile)
  - API gateway/layer
  - Backend services
  - Databases (primary + replicas)
  - Caching layer (Redis)
  - External services (OAuth, S3, etc.)

#### Accessing Architecture Documents

**Via REST API**:
```bash
GET /api/tech-spec/sessions/{session_id}/trd
```

**Response includes**:
```json
{
  "document": {
    "trd_content": "# TRD\n\n## 3. System Architecture\n...",
    "architecture_diagram": "flowchart TB\n    A[Next.js] --> B[NestJS]...",
    "database_schema": {
      "ddl": "CREATE TABLE users...",
      "erd": "erDiagram\n    USERS ||--o{ TASKS..."
    },
    ...
  }
}
```

**Quality Validation**:
- Structure check: Section 3 exists with >= 300 characters
- Architecture Agent review: Specialized LLM scores 0-100
- Overall TRD score: >= 90/100 required

**See `ARCHITECTURE_GENERATION_PROCESS.md` for complete visual workflow.**

---

### Integration Points

1. **Database Foreign Key**: `tech_spec_sessions.design_job_id → shared.design_jobs.job_id`
2. **Data Flow**: Design Agent writes to `shared.design_outputs` → Tech Spec Agent reads via `design_agent_loader.py`
3. **Workflow Handoff**: Design Agent completes → ANYON triggers Tech Spec Agent via REST API
4. **Architecture Outputs**: Tech Spec Agent generates TRD + Architecture diagrams → Backlog Agent consumes

---

**Configuration Status**: ✅ Ready for Integration (schema fixes applied)
**Estimated Setup Time**: 2-3 hours (including testing)
**Difficulty**: Medium
