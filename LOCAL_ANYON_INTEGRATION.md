# Local ANYON Integration Guide

**Last Updated**: 2025-01-16
**ANYON Architecture**: Local-First Multi-Agent Kanban Board
**Tech Spec Agent Version**: 19 nodes, 5 conditional branches

---

## Executive Summary

ANYON has pivoted from a cloud-based multi-agent platform to a **local-first AI Kanban board**. This guide shows how to integrate the Tech Spec Agent into the simplified local architecture, removing 90% of cloud infrastructure complexity while maintaining core functionality.

**Key Changes**:
- ✅ Keep: Multi-agent workflow, LangGraph core, Tech Spec generation
- ❌ Remove: API Gateway, webhooks, PostgreSQL NOTIFY, message queues, cloud deployment
- 🔄 Simplify: File-based or local database communication between agents

---

## Section 1: Local Architecture Overview

### Current (Cloud-Focused) vs. Target (Local-First)

**Current Architecture** (Over-engineered for local use):
```
┌─────────────────────────────────────────────────────────┐
│  ANYON Platform (Cloud)                                 │
│  ├── API Gateway (Kong/Nginx)                           │
│  ├── Webhook Endpoints                                  │
│  ├── PostgreSQL (port 5432) - Shared database           │
│  │   └── PostgreSQL NOTIFY/LISTEN event bus             │
│  ├── Redis (port 6379) - Distributed cache              │
│  ├── Message Queue (RabbitMQ/Redis Streams)             │
│  └── Service Mesh / Kubernetes Ingress                  │
└─────────────────────────────────────────────────────────┘
         │
         ├── Design Agent (port 8001)
         ├── Tech Spec Agent (port 8000)
         └── Backlog Agent (port 8002)
```

**Target Architecture** (Local-First):
```
┌─────────────────────────────────────────────────────────┐
│  ANYON Local Kanban Board (Desktop App)                │
│  ├── Electron/Tauri wrapper                             │
│  ├── React UI (Kanban interface)                        │
│  └── Local WebSocket (port 3000)                        │
└─────────────────────────────────────────────────────────┘
         │
         ├── Design Agent (localhost process)
         ├── Tech Spec Agent (localhost process)
         └── Backlog Agent (localhost process)
              │
              └── Shared Communication Layer:
                  Option A: File-based (./outputs/ directory)
                  Option B: SQLite database (./anyon.db)
                  Option C: Local HTTP API (localhost:800X)
```

---

## Section 2: Communication Options Comparison

### Option A: File-Based Integration (✅ RECOMMENDED for Local-First)

**Pros**:
- Simplest to implement
- No database setup required
- Easy to debug (just inspect JSON files)
- Agents can run independently
- Built-in audit trail (files are persistent)

**Cons**:
- Polling overhead (checking for new files)
- Race conditions if not careful with file locks
- No built-in rollback/transactions

**Implementation**:
```
./anyon-workspace/
├── projects/
│   └── project-<uuid>/
│       ├── design/
│       │   ├── design_job.json          # Design Agent output
│       │   ├── prd.md
│       │   ├── design_system.json
│       │   ├── ux_flow.json
│       │   ├── screen_specs.json
│       │   └── ai_studio_code.zip
│       ├── tech-spec/
│       │   ├── tech_spec_session.json   # Tech Spec Agent output
│       │   ├── trd.md
│       │   ├── api_spec.yaml
│       │   ├── db_schema.sql
│       │   ├── architecture.mmd
│       │   └── tech_stack.md
│       └── backlog/
│           └── backlog_items.json       # Backlog Agent output
└── .anyon-lock                          # Global lock file
```

**File Schema Example** (`design_job.json`):
```json
{
  "job_id": "uuid",
  "project_id": "uuid",
  "status": "completed",
  "completed_at": "2025-01-16T10:30:00Z",
  "outputs": {
    "prd_path": "./prd.md",
    "design_system_path": "./design_system.json",
    "ux_flow_path": "./ux_flow.json",
    "screen_specs_path": "./screen_specs.json",
    "ai_studio_code_path": "./ai_studio_code.zip"
  },
  "user_decisions": [...]
}
```

---

### Option B: Local SQLite Database

**Pros**:
- Structured queries (no file parsing)
- ACID transactions
- Built-in concurrency control
- Smaller footprint than PostgreSQL

**Cons**:
- Still requires database setup
- Migration complexity (Alembic for SQLite)
- Single-writer limitation (SQLite WAL mode helps)

**Implementation**:
```python
# config.py
DATABASE_URL = "sqlite:///./anyon.db"  # Instead of PostgreSQL

# All agents connect to same local SQLite file
# Use polling: SELECT * FROM jobs WHERE status = 'completed' AND processed = false
```

---

### Option C: Local HTTP API (Current Architecture)

**Pros**:
- Minimal code changes (already implemented)
- RESTful interface (well-understood pattern)
- Real-time WebSocket for UI

**Cons**:
- Requires FastAPI server running
- More overhead than files
- Port conflicts if multiple users

**Implementation**:
```python
# Each agent runs on localhost
Design Agent:    http://localhost:8001
Tech Spec Agent: http://localhost:8000
Backlog Agent:   http://localhost:8002

# Design Agent calls: POST http://localhost:8000/api/projects/{id}/start-tech-spec
# Tech Spec Agent calls: POST http://localhost:8002/api/backlog/create
```

---

### Recommendation Matrix

| Criterion | File-Based | SQLite | Local API |
|-----------|------------|--------|-----------|
| Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Code Changes | Minimal | Medium | Minimal |
| Performance | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Debugging | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Scalability | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Local-First Fit | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**Winner**: **File-Based Integration** for local-first use case

---

## Section 3: Database Simplification

### Option 1: Keep PostgreSQL (Lightweight Mode)

If you still want a database but local-only:

```yaml
# docker-compose.local.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: anyon_local
      POSTGRES_USER: anyon
      POSTGRES_PASSWORD: local123
    ports:
      - "5432:5432"
    volumes:
      - ./local-data/postgres:/var/lib/postgresql/data  # Local directory

  tech-spec-agent:
    build: .
    environment:
      DATABASE_URL: postgresql://anyon:local123@postgres:5432/anyon_local
      REDIS_URL: redis://redis:6379/0
      MODE: local  # New flag
```

**Changes Required**:
- Remove `shared.*` schema complexity (all tables in `public` schema)
- Remove foreign keys to other agent schemas
- Each agent owns its own tables

---

### Option 2: Migrate to SQLite

**Step 1**: Update `src/config.py`

```python
# OLD (lines 31-34)
database_url: str = Field(
    default="postgresql://user:pass@localhost:5432/tech_spec_db"
)

# NEW
database_mode: str = Field(default="local")  # "local" or "cloud"
database_url: str = Field(
    default_factory=lambda: (
        "sqlite:///./anyon.db" if os.getenv("MODE") == "local"
        else "postgresql://user:pass@localhost:5432/tech_spec_db"
    )
)
```

**Step 2**: Update Alembic for SQLite compatibility

```python
# alembic/versions/001_initial_schema.py

# REMOVE (not supported in SQLite):
- op.execute('CREATE SCHEMA IF NOT EXISTS shared')
- All "schema='shared'" arguments
- PostgreSQL-specific types: JSONB → JSON

# CHANGE:
- Column(postgresql.JSONB) → Column(JSON)
- Column(postgresql.UUID) → Column(String(36))  # UUID as string in SQLite
```

**Step 3**: Fix the foreign key bug while migrating

```python
# OLD (line 41 - WRONG):
sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.id'])

# NEW (SQLite):
sa.ForeignKeyConstraint(['design_job_id'], ['design_jobs.job_id'])
# Note: No 'shared.' schema prefix, use 'job_id' column
```

**Step 4**: Create SQLite-compatible migration

```bash
# Generate new migration
alembic revision --autogenerate -m "sqlite_compatible_schema"

# Apply migration
alembic upgrade head
```

---

## Section 4: Remove Cloud Infrastructure

### Files to Delete or Comment Out

**Delete Entire Files**:
```
❌ monitoring/prometheus.yml          # Cloud monitoring
❌ monitoring/grafana/                # Cloud dashboards
❌ .github/workflows/deploy.yml       # Cloud deployment
❌ scripts/deploy-to-aws.sh           # Cloud deployment script
```

**Comment Out or Remove Sections**:

1. **src/config.py (lines 55-58)** - ANYON cloud platform config:
```python
# REMOVE (cloud-only):
# anyon_api_base_url: str = Field(...)
# anyon_webhook_secret: str = Field(...)
# anyon_frontend_url: str = Field(...)

# KEEP:
workspace_path: str = Field(default="./anyon-workspace")  # NEW
```

2. **src/api/endpoints.py** - Remove webhook handlers:
```python
# REMOVE:
@router.post("/webhooks/design-agent-complete")
async def handle_design_agent_webhook(...):  # Not needed for local

@router.post("/webhooks/backlog-agent-ready")
async def handle_backlog_agent_webhook(...):  # Not needed for local
```

3. **src/langgraph/nodes/persistence_nodes.py (lines 109-210)** - Remove PostgreSQL NOTIFY:
```python
# REMOVE (lines 177-210):
# async with pool.acquire() as conn:
#     await conn.execute(
#         f"NOTIFY anyon_agent_events, '{json.dumps(event_data)}'"
#     )

# REPLACE WITH (file-based):
async def notify_next_agent_node(state: TechSpecState) -> TechSpecState:
    """Write completion signal for Backlog Agent (file-based)"""
    signal_path = (
        f"{settings.workspace_path}/projects/{state['project_id']}/"
        f"tech-spec/completion_signal.json"
    )

    with open(signal_path, 'w') as f:
        json.dump({
            "tech_spec_session_id": state["session_id"],
            "project_id": state["project_id"],
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }, f, indent=2)

    return state
```

4. **docker-compose.yml** - Simplify services:
```yaml
# REMOVE:
- prometheus service
- grafana service
- pgadmin service (optional)

# KEEP:
- postgres (if using PostgreSQL) OR comment out if using SQLite
- redis (for caching only)
- tech-spec-agent
```

---

## Section 5: Kanban UI Integration

### Real-Time Progress Updates

The Kanban board needs to show Tech Spec Agent progress in real-time.

**Keep WebSocket** (already implemented):
```typescript
// Kanban UI connects to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/tech-spec/SESSION_ID?token=JWT');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'progress_update':
      updateKanbanCard({
        taskId: 'tech-spec-task',
        progress: data.progress,  // 0-100
        status: data.message
      });
      break;

    case 'agent_message':
      // Show decision prompt in Kanban card
      showDecisionModal(data.message, data.options);
      break;

    case 'completion':
      // Move card to "Tech Spec Complete" column
      moveCard('tech-spec-task', 'completed');
      break;
  }
};
```

### Kanban Card Schema

```json
{
  "id": "tech-spec-<session_id>",
  "title": "Generate Technical Requirements",
  "status": "in_progress",
  "progress": 45,
  "currentStage": "research_technologies",
  "assignedAgent": "tech-spec-agent",
  "dependencies": ["design-<job_id>"],
  "outputs": {
    "trd_url": "./projects/<id>/tech-spec/trd.md",
    "api_spec_url": "./projects/<id>/tech-spec/api_spec.yaml"
  },
  "metadata": {
    "started_at": "2025-01-16T10:00:00Z",
    "estimated_completion": "2025-01-16T10:25:00Z"
  }
}
```

### Kanban Board → Tech Spec Agent Communication

When user makes a decision in the Kanban UI:

```typescript
// User clicks "Option 2" for technology choice
ws.send(JSON.stringify({
  type: 'user_message',
  sessionId: 'SESSION_ID',
  message: '2',  // Selected option number
  context: {
    category: 'Authentication',
    timestamp: new Date().toISOString()
  }
}));

// Tech Spec Agent receives via existing WebSocket handler
// src/websocket/routes.py:238
// await job_processor.process_user_decision(session_id, decision)
```

**No changes needed** - WebSocket implementation already supports this!

---

## Section 6: Implementation Steps

### Step 1: Choose Integration Method

**Recommended**: File-Based Integration

**Decision Checklist**:
- [ ] Will multiple users run ANYON simultaneously on same machine? → If yes, use SQLite
- [ ] Do you need transaction guarantees? → If yes, use SQLite
- [ ] Do you want simplest possible setup? → If yes, use File-Based
- [ ] Do you want to keep current code mostly unchanged? → If yes, use Local API

**For this guide, we'll proceed with File-Based Integration.**

---

### Step 2: Implement File-Based Communication

**2.1: Create File Utilities Module**

Create new file: `src/integration/local_file_connector.py`

```python
"""
Local file-based communication for multi-agent workflow.
Replaces PostgreSQL NOTIFY/LISTEN with file system polling.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import fcntl  # File locking (Unix) or msvcrt (Windows)


class LocalFileConnector:
    """Handles file-based communication between agents."""

    def __init__(self, workspace_path: str = "./anyon-workspace"):
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_id: str) -> Path:
        """Get project directory path."""
        path = self.workspace / "projects" / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_design_output(self, project_id: str) -> Optional[Dict]:
        """
        Read Design Agent output for a project.

        Returns None if design job not complete.
        """
        design_job_path = (
            self.get_project_path(project_id) / "design" / "design_job.json"
        )

        if not design_job_path.exists():
            return None

        with open(design_job_path, 'r') as f:
            data = json.load(f)

        if data.get("status") != "completed":
            return None

        return data

    def load_design_documents(self, project_id: str) -> Dict[str, str]:
        """
        Load all design documents (PRD, design system, etc.)

        Equivalent to src/integration/design_agent_loader.py
        but reads from files instead of database.
        """
        design_output = self.read_design_output(project_id)
        if not design_output:
            raise ValueError(f"Design job not complete for project {project_id}")

        base_path = self.get_project_path(project_id) / "design"

        documents = {}
        for doc_type, file_path in design_output["outputs"].items():
            full_path = base_path / file_path
            if full_path.suffix == '.json':
                with open(full_path, 'r') as f:
                    documents[doc_type] = json.load(f)
            else:  # .md, .yaml, etc.
                with open(full_path, 'r', encoding='utf-8') as f:
                    documents[doc_type] = f.read()

        return documents

    def write_tech_spec_output(
        self,
        project_id: str,
        session_id: str,
        documents: Dict[str, str]
    ) -> None:
        """
        Write Tech Spec Agent output files.

        Args:
            project_id: Project UUID
            session_id: Tech Spec session UUID
            documents: Dict of {doc_type: content}
                - trd: Markdown content
                - api_spec: YAML content
                - db_schema: SQL content
                - architecture: Mermaid content
                - tech_stack: Markdown content
        """
        tech_spec_path = self.get_project_path(project_id) / "tech-spec"
        tech_spec_path.mkdir(parents=True, exist_ok=True)

        # Write session metadata
        session_data = {
            "session_id": session_id,
            "project_id": project_id,
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "outputs": {}
        }

        # Write each document
        file_map = {
            "trd": "trd.md",
            "api_spec": "api_spec.yaml",
            "db_schema": "db_schema.sql",
            "architecture": "architecture.mmd",
            "tech_stack": "tech_stack.md"
        }

        for doc_type, content in documents.items():
            if doc_type in file_map:
                file_name = file_map[doc_type]
                file_path = tech_spec_path / file_name

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                session_data["outputs"][doc_type] = f"./{file_name}"

        # Write session file (for Backlog Agent to read)
        with open(tech_spec_path / "tech_spec_session.json", 'w') as f:
            json.dump(session_data, f, indent=2)

    def notify_backlog_agent(self, project_id: str) -> None:
        """
        Signal Backlog Agent that Tech Spec is complete.

        Replaces PostgreSQL NOTIFY.
        """
        signal_path = (
            self.get_project_path(project_id) / "tech-spec" / "completion_signal.json"
        )

        with open(signal_path, 'w') as f:
            json.dump({
                "event_type": "tech_spec_complete",
                "project_id": project_id,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
```

**2.2: Update Load Inputs Node**

Modify `src/langgraph/nodes/load_inputs.py`:

```python
# ADD import
from src.integration.local_file_connector import LocalFileConnector

async def load_inputs_node(state: TechSpecState) -> TechSpecState:
    """
    Load PRD and design documents from Design Agent outputs.

    LOCAL MODE: Read from file system
    CLOUD MODE: Read from PostgreSQL (existing code)
    """
    # NEW: Check if running in local mode
    if settings.mode == "local":
        connector = LocalFileConnector(settings.workspace_path)

        try:
            # Read design documents from files
            documents = connector.load_design_documents(state["project_id"])

            state.update({
                "prd_content": documents.get("prd", ""),
                "design_docs": {
                    "design_system": documents.get("design_system", ""),
                    "ux_flow": documents.get("ux_flow", ""),
                    "screen_specs": documents.get("screen_specs", "")
                },
                "ai_studio_code_path": documents.get("ai_studio_code_path", ""),
                "current_stage": "load_inputs",
                "progress_percentage": 5.0
            })

            return state

        except Exception as e:
            state["errors"].append({
                "node": "load_inputs",
                "error_type": "FileLoadError",
                "message": f"Failed to load design documents: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            return state

    # EXISTING CODE for cloud mode (PostgreSQL)
    else:
        # ... existing load_design_agent_outputs() code ...
        pass
```

**2.3: Update Save to DB Node**

Modify `src/langgraph/nodes/persistence_nodes.py`:

```python
# ADD import
from src.integration.local_file_connector import LocalFileConnector

async def save_to_db_node(state: TechSpecState) -> TechSpecState:
    """
    Save generated documents.

    LOCAL MODE: Write to file system
    CLOUD MODE: Write to PostgreSQL (existing code)
    """
    if settings.mode == "local":
        connector = LocalFileConnector(settings.workspace_path)

        documents = {
            "trd": state["trd_draft"],
            "api_spec": state["api_specification"],
            "db_schema": state["database_schema"],
            "architecture": state["architecture_diagram"],
            "tech_stack": state["tech_stack_document"]
        }

        connector.write_tech_spec_output(
            project_id=state["project_id"],
            session_id=state["session_id"],
            documents=documents
        )

        state.update({
            "current_stage": "save_to_db",
            "progress_percentage": 95.0
        })

        return state

    # EXISTING CODE for cloud mode (PostgreSQL)
    else:
        # ... existing database save code ...
        pass


async def notify_next_agent_node(state: TechSpecState) -> TechSpecState:
    """
    Notify Backlog Agent of completion.

    LOCAL MODE: Write completion signal file
    CLOUD MODE: PostgreSQL NOTIFY (existing code)
    """
    if settings.mode == "local":
        connector = LocalFileConnector(settings.workspace_path)
        connector.notify_backlog_agent(state["project_id"])

        state.update({
            "current_stage": "notify_next_agent",
            "progress_percentage": 100.0,
            "completed": True
        })

        return state

    # EXISTING CODE for cloud mode (PostgreSQL NOTIFY)
    else:
        # ... existing NOTIFY code ...
        pass
```

---

### Step 3: Update Configuration

**3.1: Add Local Mode Flag**

Edit `src/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # NEW: Local vs Cloud mode
    mode: str = Field(
        default="local",
        description="Deployment mode: 'local' or 'cloud'"
    )

    workspace_path: str = Field(
        default="./anyon-workspace",
        description="Local workspace directory for file-based communication"
    )

    # CONDITIONAL: Database URL based on mode
    @property
    def effective_database_url(self) -> str:
        if self.mode == "local":
            return "sqlite:///./anyon.db"
        else:
            return self.database_url
```

**3.2: Update .env.example**

```bash
# Deployment Mode
MODE=local  # Options: local, cloud

# Local Workspace (file-based integration)
WORKSPACE_PATH=./anyon-workspace

# Database (local mode uses SQLite automatically)
DATABASE_URL=sqlite:///./anyon.db

# Redis Cache (optional in local mode)
REDIS_URL=redis://localhost:6379/0

# LLM API Keys (required)
ANTHROPIC_API_KEY=your-key-here
TAVILY_API_KEY=your-key-here

# JWT Secret (for local auth)
JWT_SECRET=local-secret-change-in-production
```

---

### Step 4: Connect to Kanban UI

**4.1: Kanban Board Directory Watcher**

The Kanban UI can watch for file changes:

```typescript
// kanban/services/agentWatcher.ts
import chokidar from 'chokidar';

class AgentWatcher {
  private watcher: chokidar.FSWatcher;

  startWatching(projectId: string, callbacks: {
    onTechSpecComplete: (data: any) => void;
  }) {
    const watchPath = `./anyon-workspace/projects/${projectId}/tech-spec/`;

    this.watcher = chokidar.watch(watchPath, {
      ignoreInitial: true,
      depth: 1
    });

    this.watcher.on('add', (path) => {
      if (path.endsWith('completion_signal.json')) {
        // Tech Spec completed!
        const data = JSON.parse(fs.readFileSync(path, 'utf-8'));
        callbacks.onTechSpecComplete(data);
      }
    });
  }
}
```

**4.2: WebSocket for Real-Time Updates** (already implemented!)

The existing WebSocket in `src/websocket/routes.py` works perfectly for local mode:

```typescript
// Kanban UI connects same way
const ws = new WebSocket(`ws://localhost:8000/ws/tech-spec/${sessionId}?token=${jwt}`);

// No changes needed! WebSocket works for both local and cloud
```

---

### Step 5: Test Local Multi-Agent Workflow

**5.1: Setup Test Project**

```bash
# Create test project structure
mkdir -p anyon-workspace/projects/test-project-001/design
cd anyon-workspace/projects/test-project-001/design

# Create mock Design Agent output
cat > design_job.json <<EOF
{
  "job_id": "design-001",
  "project_id": "test-project-001",
  "status": "completed",
  "completed_at": "2025-01-16T10:00:00Z",
  "outputs": {
    "prd": "./prd.md",
    "design_system": "./design_system.json",
    "ux_flow": "./ux_flow.json",
    "screen_specs": "./screen_specs.json",
    "ai_studio_code": "./ai_studio_code.zip"
  }
}
EOF

# Create mock PRD
cat > prd.md <<EOF
# Product Requirements Document

## Overview
Build a task management app with AI-powered suggestions.

## Features
- User authentication
- Task CRUD operations
- AI task prioritization
- Real-time collaboration

## Tech Stack
- Frontend: TBD (to be decided by Tech Spec Agent)
- Backend: TBD
- Database: TBD
EOF
```

**5.2: Run Tech Spec Agent in Local Mode**

```bash
# Set environment
export MODE=local
export WORKSPACE_PATH=./anyon-workspace

# Run agent
python -m uvicorn src.main:app --reload --port 8000

# Trigger via API
curl -X POST http://localhost:8000/api/projects/test-project-001/start-tech-spec \
  -H "Content-Type: application/json" \
  -d '{"design_job_id": "design-001"}'
```

**5.3: Verify Output Files**

```bash
# After workflow completes, check output
ls -la anyon-workspace/projects/test-project-001/tech-spec/

# Expected files:
# - tech_spec_session.json
# - trd.md
# - api_spec.yaml
# - db_schema.sql
# - architecture.mmd
# - tech_stack.md
# - completion_signal.json  (for Backlog Agent)
```

---

## Section 7: Code Changes Required - Complete Checklist

### Files to CREATE

- [ ] `src/integration/local_file_connector.py` (File-based communication layer)
- [ ] `LOCAL_ANYON_INTEGRATION.md` (This guide)

### Files to MODIFY

- [ ] `src/config.py`
  - Add `mode` field (local/cloud)
  - Add `workspace_path` field
  - Add `effective_database_url` property

- [ ] `src/langgraph/nodes/load_inputs.py`
  - Add file-based loading for local mode
  - Keep PostgreSQL loading for cloud mode

- [ ] `src/langgraph/nodes/persistence_nodes.py`
  - Add file-based saving for local mode (lines 65-90)
  - Add file-based notification for local mode (lines 150-175)
  - Keep PostgreSQL NOTIFY for cloud mode

- [ ] `.env.example`
  - Add MODE=local
  - Add WORKSPACE_PATH=./anyon-workspace

- [ ] `docker-compose.yml` (optional)
  - Add local mode service configuration

### Files to DELETE (Cloud-Only)

- [ ] `monitoring/prometheus.yml`
- [ ] `monitoring/grafana/`
- [ ] `scripts/deploy-to-aws.sh`
- [ ] `.github/workflows/deploy.yml` (or modify for local testing only)

### Configuration Changes

- [ ] Update `.env` to set `MODE=local`
- [ ] Create `anyon-workspace/` directory structure
- [ ] (Optional) Migrate to SQLite: Update Alembic migrations

---

## Section 8: Testing Local Workflow - End-to-End

### Test Scenario: Full Multi-Agent Workflow

**Actors**:
- Design Agent (manual simulation via files)
- Tech Spec Agent (your agent)
- Backlog Agent (manual verification via files)
- Kanban UI (WebSocket connection)

**Step-by-Step Test**:

1. **Simulate Design Agent Completion**
   ```bash
   ./scripts/test/create-mock-design-output.sh test-project-001
   ```

2. **Start Tech Spec Agent**
   ```bash
   MODE=local python -m uvicorn src.main:app --reload --port 8000
   ```

3. **Connect Kanban UI (WebSocket)**
   ```bash
   # In browser console or Node.js script
   const ws = new WebSocket('ws://localhost:8000/ws/tech-spec/SESSION_ID?token=TEST_JWT');
   ws.onmessage = (e) => console.log(JSON.parse(e.data));
   ```

4. **Trigger Tech Spec Workflow**
   ```bash
   curl -X POST http://localhost:8000/api/projects/test-project-001/start-tech-spec \
     -H "Authorization: Bearer TEST_JWT" \
     -H "Content-Type: application/json" \
     -d '{"design_job_id": "design-001"}'
   ```

5. **Monitor Progress**
   - Watch WebSocket messages in console
   - Make technology decisions when prompted
   - Observe progress updates

6. **Verify Output Files**
   ```bash
   ls -la anyon-workspace/projects/test-project-001/tech-spec/
   cat anyon-workspace/projects/test-project-001/tech-spec/trd.md
   ```

7. **Verify Backlog Agent Signal**
   ```bash
   cat anyon-workspace/projects/test-project-001/tech-spec/completion_signal.json
   # Should contain: {"event_type": "tech_spec_complete", ...}
   ```

8. **Verify Kanban Card Update**
   - Kanban UI should move card to "Completed" column
   - Display links to generated documents

### Debugging Local Integration

**Common Issues**:

1. **Design output not found**
   - Check: `anyon-workspace/projects/{project_id}/design/design_job.json` exists
   - Check: `status` field is `"completed"`
   - Check: File permissions allow reading

2. **File write errors**
   - Check: Directory permissions
   - Check: `WORKSPACE_PATH` environment variable is set correctly
   - Check: Disk space available

3. **WebSocket connection fails**
   - Check: FastAPI server is running on port 8000
   - Check: JWT token is valid (or use test mode without auth)
   - Check: Firewall allows localhost:8000

4. **Backlog Agent doesn't detect completion**
   - Check: `completion_signal.json` was created
   - Check: Backlog Agent is watching correct directory
   - Check: File watcher is running (chokidar, watchdog, etc.)

---

## Appendix A: Migration Checklist

### From Cloud to Local Deployment

**Phase 1: Preparation (1 hour)**
- [ ] Backup current code to new branch `git checkout -b local-integration`
- [ ] Review this guide completely
- [ ] Choose integration method (File-Based recommended)

**Phase 2: Core Changes (2-4 hours)**
- [ ] Create `local_file_connector.py`
- [ ] Update `config.py` with mode flag
- [ ] Modify `load_inputs.py` for file-based loading
- [ ] Modify `persistence_nodes.py` for file-based saving

**Phase 3: Testing (2 hours)**
- [ ] Create test project with mock Design Agent output
- [ ] Run Tech Spec Agent in local mode
- [ ] Verify all output files are created
- [ ] Test WebSocket connection

**Phase 4: Cleanup (1 hour)**
- [ ] Remove cloud-specific files
- [ ] Update README.md with local instructions
- [ ] Update docker-compose.yml (if using)
- [ ] Test fresh deployment from scratch

**Total Estimated Time**: 6-8 hours

---

## Appendix B: File Schema Specifications

### design_job.json
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["job_id", "project_id", "status", "completed_at", "outputs"],
  "properties": {
    "job_id": {"type": "string", "format": "uuid"},
    "project_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["in_progress", "completed", "failed"]},
    "completed_at": {"type": "string", "format": "date-time"},
    "outputs": {
      "type": "object",
      "properties": {
        "prd": {"type": "string"},
        "design_system": {"type": "string"},
        "ux_flow": {"type": "string"},
        "screen_specs": {"type": "string"},
        "ai_studio_code": {"type": "string"}
      }
    }
  }
}
```

### tech_spec_session.json
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["session_id", "project_id", "status", "completed_at", "outputs"],
  "properties": {
    "session_id": {"type": "string", "format": "uuid"},
    "project_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["in_progress", "completed", "failed"]},
    "completed_at": {"type": "string", "format": "date-time"},
    "outputs": {
      "type": "object",
      "properties": {
        "trd": {"type": "string"},
        "api_spec": {"type": "string"},
        "db_schema": {"type": "string"},
        "architecture": {"type": "string"},
        "tech_stack": {"type": "string"}
      }
    }
  }
}
```

---

## Conclusion

This local integration approach:
- ✅ Removes 90% of cloud infrastructure complexity
- ✅ Maintains core Tech Spec Agent functionality (19 nodes, LangGraph workflow)
- ✅ Enables simple multi-agent communication via files
- ✅ Supports Kanban UI integration via WebSocket (no changes needed!)
- ✅ Can be implemented in 6-8 hours

**Next Steps**:
1. Review this guide with your team
2. Choose integration method (File-Based recommended)
3. Implement core changes (Step 6: Implementation Steps)
4. Test with mock Design Agent output
5. Integrate with Kanban UI
6. Deploy to users

**Questions? Issues?**
- Check Appendix B for file schemas
- Refer to existing code in `src/integration/design_agent_loader.py` for reference
- Test each step incrementally
- Use file system debugging (just inspect JSON files!)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-16
**Maintained By**: Tech Spec Agent Team
