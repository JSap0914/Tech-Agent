# 🚀 Tech Spec Agent + Design Agent Integration Setup

**Status**: ✅ Auto-configured and ready to run!
**Estimated Setup Time**: 15-30 minutes

---

## ✅ What I've Already Done For You

I've automatically configured everything except what requires your input:

1. ✅ **Fixed the database migration** (foreign key issue resolved)
2. ✅ **Created .env files** for both agents with shared credentials
3. ✅ **Created database setup script** (`setup_database.sql`)
4. ✅ **Created integration test script** (`test_integration.py`)
5. ✅ **Created startup scripts** for easy launching

---

## 📋 What YOU Need to Do

### **1. Get API Keys** (5 minutes)

You need to obtain these API keys:

#### ✅ **Already Have:**
- Anthropic API Key (already in Design Agent .env)

#### ⚠️ **Need to Get:**

**Tavily API (for Tech Spec Agent):**
1. Go to https://tavily.com/
2. Sign up for a free account
3. Get your API key
4. Open `Tech Agent/.env`
5. Replace `tvly-YOUR_TAVILY_API_KEY_HERE` with your real key

**Optional (for Design Agent web search):**
- GitHub Token: https://github.com/settings/tokens (needs `public_repo` scope)
- Google API Key: https://console.cloud.google.com/apis/credentials
- Google Search Engine ID: https://programmablesearchengine.google.com/

---

### **2. Install Prerequisites** (10 minutes)

#### **Check if PostgreSQL is running:**

```bash
# Check PostgreSQL status
psql --version

# If not installed, download from: https://www.postgresql.org/download/windows/
```

#### **Check if Redis is running:**

```bash
# Check Redis status
redis-cli ping
# Should return: PONG

# If not installed, download from: https://redis.io/download
# Or use: https://github.com/tporadowski/redis/releases (Windows)
```

#### **Start Redis (if not running):**

```bash
# In a new terminal:
redis-server
```

---

### **3. Set Up Database** (5 minutes)

```bash
# Run the database setup script
psql -U postgres -f "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent\setup_database.sql"

# Enter your PostgreSQL superuser password when prompted
```

This will:
- ✅ Create `anyon_db` database
- ✅ Create `anyon_user` with password `anyon_password_2025`
- ✅ Create schemas: `shared`, `design_agent`, `public`
- ✅ Grant all necessary permissions

---

### **4. Install Python Dependencies** (10 minutes)

#### **Design Agent:**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"

# Create virtual environment (if not exists)
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### **Tech Spec Agent:**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Create virtual environment (if not exists)
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### **5. Run Database Migrations** (2 minutes)

#### **Design Agent (FIRST):**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
venv\Scripts\activate

# Run migrations
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 20250113_0001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 20250113_0001 -> 20250113_0002, anyon_views
```

#### **Tech Spec Agent (SECOND):**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
venv\Scripts\activate

# Run migrations
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_fix_trd_jsonb_columns
```

#### **Verify Tables Created:**

```bash
psql -U anyon_user -d anyon_db

# Check shared tables (created by Design Agent)
\dt shared.*

# Check Tech Spec tables
\dt

# Check foreign key
\d tech_spec_sessions
```

---

### **6. Update Tavily API Key** (1 minute)

Open `Tech Agent/.env` and replace:

```bash
# Find this line:
TAVILY_API_KEY=tvly-YOUR_TAVILY_API_KEY_HERE

# Replace with your real key:
TAVILY_API_KEY=tvly-abc123def456...
```

---

### **7. Start Both Agents** (2 minutes)

#### **Terminal 1: Design Agent**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"

# Double-click this file, or run:
start_design_agent.bat
```

**Expected output:**
```
========================================
 Design Agent is running!
 Listening for jobs on shared.design_jobs
 Press Ctrl+C to stop
========================================
INFO: Design Agent job listener started
INFO: Listening for new jobs...
```

#### **Terminal 2: Tech Spec Agent**

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Double-click this file, or run:
start_tech_spec_agent.bat
```

**Expected output:**
```
========================================
 Tech Spec Agent is running!
 API: http://localhost:8001
 Docs: http://localhost:8001/docs
 Health: http://localhost:8001/health
 Press Ctrl+C to stop
========================================
INFO: Application startup complete
```

---

### **8. Verify Everything Works** (2 minutes)

#### **Test 1: Health Checks**

```bash
# Check Tech Spec Agent health
curl http://localhost:8001/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "tech-spec-agent",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

#### **Test 2: API Docs**

Open in browser:
- http://localhost:8001/docs

You should see the FastAPI interactive docs!

---

### **9. Run Integration Test** (OPTIONAL, 45-60 minutes)

This will test the full flow from Design Agent → Tech Spec Agent:

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
venv\Scripts\activate

# Run integration test
python test_integration.py
```

**What it does:**
1. Creates a test Design Job
2. Waits for Design Agent to complete (30-45 min)
3. Triggers Tech Spec Agent
4. Monitors progress via WebSocket
5. Verifies TRD generation

---

## 🎉 You're Done!

Both agents are now running and integrated!

### **What's Connected:**

```
Design Agent (Port 8000)
    ↓
PostgreSQL Database (anyon_db)
    shared.design_jobs
    shared.design_outputs
    ↓
Tech Spec Agent (Port 8001)
    tech_spec_sessions → shared.design_jobs (FK)
    ↓
Generated TRD Documents
```

### **How to Use:**

1. **Insert a Design Job** into `shared.design_jobs` table
2. **Design Agent** automatically picks it up and processes
3. When Design Agent completes, **call Tech Spec Agent API**:
   ```bash
   curl -X POST http://localhost:8001/api/projects/<project_id>/start-tech-spec \
     -H "Content-Type: application/json" \
     -d '{"design_job_id": "<design_job_id>", "user_id": "user-123"}'
   ```
4. **Tech Spec Agent** loads Design Agent outputs and generates TRD

---

## 🔧 Troubleshooting

### **"Connection refused" to database**

```bash
# Make sure PostgreSQL is running
pg_ctl status

# If not running:
pg_ctl start
```

### **"Redis connection failed"**

```bash
# Start Redis
redis-server
```

### **"ModuleNotFoundError"**

```bash
# Reinstall dependencies
cd "Design Agent"  # or "Tech Agent"
venv\Scripts\activate
pip install -r requirements.txt
```

### **"Foreign key constraint violation"**

This means you didn't run Design Agent migrations first!

```bash
# Run Design Agent migrations FIRST
cd "Design Agent"
alembic upgrade head

# Then run Tech Spec Agent migrations
cd "Tech Agent"
alembic upgrade head
```

---

## 📞 Next Steps

### **Integration with ANYON Platform:**

1. Build React frontend components:
   - `TechSpecChat.tsx` - WebSocket chat interface
   - Kanban board integration for dragging cards

2. Create ANYON API endpoints:
   - POST `/design-jobs` - Trigger Design Agent
   - GET `/design-jobs/:id` - Get Design Job status
   - POST `/tech-spec-sessions` - Trigger Tech Spec Agent
   - WebSocket connection for real-time updates

3. Set up production deployment:
   - Docker containers for both agents
   - Kubernetes or AWS ECS
   - Production PostgreSQL (RDS)
   - Production Redis (ElastiCache)

---

## 📄 Generated Files

I created these files for you:

1. **Tech Agent/alembic/versions/001_initial_schema.py** - Fixed foreign key
2. **Design Agent/.env** - Updated with shared credentials
3. **Tech Agent/.env** - Created with matching credentials
4. **Tech Agent/setup_database.sql** - Database initialization script
5. **Tech Agent/test_integration.py** - Full integration test
6. **Design Agent/start_design_agent.bat** - Easy startup script
7. **Tech Agent/start_tech_spec_agent.bat** - Easy startup script
8. **Tech Agent/SETUP_GUIDE.md** - This file!

---

## ✅ Quick Checklist

Before starting, ensure you have:

- [ ] PostgreSQL 14+ installed and running
- [ ] Redis installed and running
- [ ] Python 3.11+ installed
- [ ] Anthropic API key (already in Design Agent .env)
- [ ] Tavily API key (add to Tech Agent .env)
- [ ] Virtual environments created for both agents
- [ ] Dependencies installed for both agents
- [ ] Database created with `setup_database.sql`
- [ ] Design Agent migrations run (FIRST)
- [ ] Tech Spec Agent migrations run (SECOND)
- [ ] Both agents started and health checks passing

---

**Setup complete! 🎉**

If you need help, refer to:
- **INTEGRATION_CONFIGURATION_GUIDE.md** - Detailed technical documentation
- **Tech Spec Agent API Docs**: http://localhost:8001/docs
