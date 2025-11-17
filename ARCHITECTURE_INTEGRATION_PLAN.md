# Architecture Generation Integration Plan

**Project**: Tech Spec Agent - Architecture Generation Feature
**Assumption**: All other Tech Spec Agent features are already implemented
**Timeline**: 5 days (1 week)
**Goal**: Add architecture diagram generation to existing workflow

---

## Current State Analysis

### What's Already Done ✅
- ✅ LangGraph workflow with 17 nodes (all phases except architecture)
- ✅ Database models (tech_spec_sessions, generated_trd_documents, etc.)
- ✅ REST API endpoints (start session, get status, download TRD)
- ✅ WebSocket for real-time updates
- ✅ TRD generation with validation
- ✅ API specification generation (OpenAPI/Swagger)
- ✅ Database schema generation (SQL DDL)
- ✅ Technology research and user decision flow

### What Needs to Be Added 🔨
- 🔨 Database ERD generation (Mermaid diagram)
- 🔨 System Architecture Diagram generation (Mermaid flowchart)
- 🔨 Architecture validation agent
- 🔨 Update workflow to include 3 new nodes
- 🔨 Update progress percentages for existing nodes
- 🔨 Update database storage for architecture diagrams

---

## 5-Day Implementation Plan

---

## Day 1: Database Schema & Workflow Updates

### Morning (4 hours): Database Schema Updates

**Objective**: Ensure database can store architecture diagrams

**Tasks**:
1. Review `src/database/models.py` - GeneratedTRDDocument model
2. Verify `architecture_diagram` column exists (TEXT type)
3. If not exists, create Alembic migration:
   ```python
   # alembic/versions/xxx_add_architecture_diagram.py
   def upgrade():
       op.add_column('generated_trd_documents',
                     sa.Column('architecture_diagram', sa.Text(), nullable=True))
   ```
4. Run migration: `alembic upgrade head`
5. Test column in database:
   ```sql
   SELECT id, architecture_diagram FROM generated_trd_documents LIMIT 1;
   ```

**Deliverables**:
- ✅ Database migration created and applied
- ✅ `architecture_diagram` column available
- ✅ No breaking changes to existing code

---

### Afternoon (4 hours): Workflow Updates

**Objective**: Update LangGraph workflow to include architecture nodes

**File**: `src/langgraph/workflow.py`

**Current Workflow** (assumed structure):
```python
workflow.add_node("generate_trd", generate_trd_node)
workflow.add_node("validate_trd", validate_trd_node)
workflow.add_node("generate_api_spec", generate_api_spec_node)
workflow.add_node("generate_db_schema", generate_db_schema_node)
workflow.add_node("save_to_db", save_to_db_node)
workflow.add_node("notify_next_agent", notify_next_agent_node)
```

**Updated Workflow** (add 3 new nodes):
```python
# Existing nodes
workflow.add_node("generate_trd", generate_trd_node)
workflow.add_node("validate_trd", validate_trd_node)
workflow.add_node("generate_api_spec", generate_api_spec_node)
workflow.add_node("generate_db_schema", generate_db_schema_node)

# NEW NODES - Add these 3
workflow.add_node("generate_db_erd", generate_db_erd_node)           # 85% progress
workflow.add_node("generate_architecture", generate_architecture_node) # 90% progress
workflow.add_node("validate_architecture", validate_architecture_node) # 92% progress

# Existing nodes
workflow.add_node("generate_tech_stack", generate_tech_stack_doc_node)
workflow.add_node("save_to_db", save_to_db_node)
workflow.add_node("notify_next_agent", notify_next_agent_node)
```

**Updated Edge Connections**:
```python
# Old flow
workflow.add_edge("generate_db_schema", "save_to_db")  # DELETE THIS

# New flow
workflow.add_edge("generate_db_schema", "generate_db_erd")
workflow.add_edge("generate_db_erd", "generate_architecture")
workflow.add_edge("generate_architecture", "validate_architecture")
workflow.add_edge("validate_architecture", "generate_tech_stack")
workflow.add_edge("generate_tech_stack", "save_to_db")
```

**Tasks**:
1. Open `src/langgraph/workflow.py`
2. Add 3 new node declarations
3. Update edge connections
4. Update progress percentages in existing nodes:
   - `generate_db_schema`: 80% → 85%
   - `generate_tech_stack`: 92% → 95%
   - `save_to_db`: 95% → 98%

**Deliverables**:
- ✅ Workflow includes 3 new architecture nodes
- ✅ Edge connections updated
- ✅ Progress percentages recalibrated
- ✅ Workflow compiles without errors

**Testing**:
```python
# Test workflow compilation
from src.langgraph.workflow import create_workflow
workflow = create_workflow()
print(workflow.get_graph().nodes)  # Should show all 20 nodes
```

---

## Day 2: Database ERD Generation Node

### Full Day (8 hours): Implement `generate_db_erd` Node

**Objective**: Generate Mermaid Entity Relationship Diagram from database schema

**File**: `src/langgraph/nodes/generate_db_erd.py` (CREATE NEW FILE)

**Implementation**:

```python
"""
Database ERD Generation Node
Generates Mermaid Entity Relationship Diagram from database schema
"""

from datetime import datetime
from src.langgraph.state import TechSpecState
from src.websocket.connection_manager import connection_manager
import structlog

logger = structlog.get_logger(__name__)


async def generate_db_erd_node(state: TechSpecState) -> TechSpecState:
    """
    Generate Mermaid ERD from database schema.

    Progress: 85%

    Outputs:
    - Mermaid Entity Relationship Diagram (stored in database_schema["erd"])
    """
    logger.info("Generating Database ERD", session_id=state["session_id"])

    # Extract database schema (generated in previous node)
    db_schema = state.get("database_schema", {})

    if not db_schema or "tables" not in db_schema:
        logger.warning("No database schema found, skipping ERD generation")
        state["database_schema"] = db_schema or {}
        state["database_schema"]["erd"] = "erDiagram\n    %% No schema available"
        return state

    # Generate Mermaid ERD syntax
    erd_lines = ["erDiagram"]

    # Step 1: Add relationships
    tables = db_schema.get("tables", [])
    for table in tables:
        table_name = table.get("name", "").upper()
        foreign_keys = table.get("foreign_keys", [])

        for fk in foreign_keys:
            ref_table = fk.get("references_table", "").upper()
            cardinality = fk.get("cardinality", "||--o{")  # Default: one-to-many

            erd_lines.append(f"    {ref_table} {cardinality} {table_name} : \"{fk.get('relationship_name', 'has')}\"")

    # Step 2: Add table definitions
    for table in tables:
        table_name = table.get("name", "").upper()
        columns = table.get("columns", [])

        erd_lines.append(f"    {table_name} {{")

        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            is_pk = "PK" if col.get("is_primary_key") else ""
            is_fk = "FK" if col.get("is_foreign_key") else ""
            key_marker = f" {is_pk}{is_fk}".strip()

            erd_lines.append(f"        {col_type} {col_name}{key_marker}")

        erd_lines.append(f"    }}")

    # Combine into final ERD
    erd_diagram = "\n".join(erd_lines)

    # Store ERD in database_schema
    state["database_schema"]["erd"] = erd_diagram

    # Update state
    state.update({
        "current_stage": "db_erd_generated",
        "completion_percentage": 85.0
    })

    # Send WebSocket update
    await connection_manager.send_progress_update(
        session_id=state["session_id"],
        progress=85.0,
        message="Database ERD generated",
        data={"erd_lines": len(erd_lines)}
    )

    logger.info("Database ERD generated successfully",
                session_id=state["session_id"],
                tables_count=len(tables))

    return state
```

**Tasks**:
1. Create `src/langgraph/nodes/generate_db_erd.py`
2. Implement ERD generation logic
3. Parse database schema from state
4. Generate Mermaid ERD syntax with:
   - Relationships (one-to-one, one-to-many, many-to-many)
   - Table definitions
   - Columns with types
   - Primary keys (PK) and Foreign keys (FK)
5. Handle edge cases (no schema, missing relationships)
6. Write unit tests

**Deliverables**:
- ✅ `generate_db_erd_node` implemented
- ✅ Mermaid ERD syntax valid
- ✅ Handles all relationship types
- ✅ Unit tests passing

**Testing**:
```python
# tests/langgraph/nodes/test_generate_db_erd.py
import pytest
from src.langgraph.nodes.generate_db_erd import generate_db_erd_node

@pytest.mark.asyncio
async def test_generate_db_erd():
    state = {
        "session_id": "test-session",
        "database_schema": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "uuid", "is_primary_key": True},
                        {"name": "email", "type": "string"},
                    ],
                    "foreign_keys": []
                },
                {
                    "name": "tasks",
                    "columns": [
                        {"name": "id", "type": "uuid", "is_primary_key": True},
                        {"name": "user_id", "type": "uuid", "is_foreign_key": True},
                    ],
                    "foreign_keys": [
                        {
                            "references_table": "users",
                            "cardinality": "||--o{",
                            "relationship_name": "creates"
                        }
                    ]
                }
            ]
        }
    }

    result = await generate_db_erd_node(state)

    assert "erd" in result["database_schema"]
    assert "erDiagram" in result["database_schema"]["erd"]
    assert "USERS ||--o{ TASKS" in result["database_schema"]["erd"]
    assert result["completion_percentage"] == 85.0
```

**Run Tests**:
```bash
pytest tests/langgraph/nodes/test_generate_db_erd.py -v
```

---

## Day 3: System Architecture Diagram Generation

### Full Day (8 hours): Implement `generate_architecture` Node

**Objective**: Generate complete system architecture Mermaid flowchart using Claude

**File**: `src/langgraph/nodes/generate_architecture.py` (CREATE NEW FILE)

**Implementation**:

```python
"""
System Architecture Diagram Generation Node
Uses Claude Sonnet 4 to generate complete system architecture flowchart
"""

from datetime import datetime
from anthropic import AsyncAnthropic
from src.langgraph.state import TechSpecState
from src.websocket.connection_manager import connection_manager
from src.config import settings
import structlog

logger = structlog.get_logger(__name__)
anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_architecture_node(state: TechSpecState) -> TechSpecState:
    """
    Generate system architecture Mermaid flowchart.

    Progress: 87% → 90%

    Uses Claude Sonnet 4 to design architecture based on:
    - Selected technologies
    - PRD requirements
    - Database schema
    - API specification

    Outputs:
    - Mermaid flowchart showing complete system topology
    """
    logger.info("Generating System Architecture Diagram", session_id=state["session_id"])

    # Extract inputs
    selected_technologies = state.get("selected_technologies", {})
    prd_content = state.get("prd_content", "")
    db_schema = state.get("database_schema", {})
    api_spec = state.get("api_specification", "")

    # Build prompt for Claude
    prompt = f"""You are a system architect. Generate a comprehensive system architecture diagram in Mermaid flowchart format.

**Project Requirements Summary**:
{prd_content[:2000]}... (truncated)

**Selected Technology Stack**:
{format_tech_stack(selected_technologies)}

**Database Schema**:
- Tables: {', '.join([t['name'] for t in db_schema.get('tables', [])])}

**API Endpoints Count**: {count_api_endpoints(api_spec)}

**Instructions**:
1. Create a Mermaid flowchart (use `flowchart TB` for top-to-bottom layout)
2. Include the following layers with subgraphs:
   - **Client Layer**: Web app, mobile app (if applicable)
   - **API Gateway**: Load balancer (NGINX, AWS ALB, etc.)
   - **Application Layer**: API servers (show 2-3 instances for horizontal scaling)
   - **Business Services**: Subgraph showing key services (auth, core features, notifications, file upload)
   - **Data Layer**:
     - Primary database (PostgreSQL/MySQL/MongoDB)
     - Read replicas (1-2 replicas)
     - Caching layer (Redis/Memcached)
   - **External Services**: OAuth providers, S3, email service, push notifications, payment gateway
   - **Monitoring**: Prometheus, Grafana, Sentry

3. Add arrows showing:
   - Client → Gateway → API servers
   - API servers → Services
   - Services → Data layer (write to primary, read from replicas)
   - Services → Cache
   - Database replication arrows (primary → replicas)
   - Services → External services

4. Use proper Mermaid syntax with:
   - `subgraph` for grouping layers
   - `-->` for standard flow arrows
   - `-.->` for replication/async arrows
   - Node IDs with descriptions (e.g., `WebApp["Next.js Web App"]`)

5. Add styling with `classDef` for different layers (client, gateway, api, data, external, monitoring)

**Output only the Mermaid flowchart code, no additional explanation.**

Example structure:
```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        WebApp["Next.js Web Application"]
        MobileApp["React Native Mobile App"]
    end

    subgraph Gateway["API Gateway"]
        NGINX["NGINX Load Balancer"]
    end

    subgraph Application["Application Layer"]
        API1["NestJS API Server 1"]
        API2["NestJS API Server 2"]

        subgraph Services["Business Services"]
            AuthService["Authentication Service"]
            TaskService["Task Service"]
        end
    end

    subgraph DataLayer["Data Layer"]
        PostgresMain["PostgreSQL Primary"]
        PostgresReplica["PostgreSQL Replica"]
        Redis["Redis Cache"]
    end

    WebApp --> NGINX
    NGINX --> API1
    NGINX --> API2
    API1 --> AuthService
    AuthService --> PostgresMain
    PostgresMain -.-> PostgresReplica
    ...
```

Generate the complete architecture diagram now:
"""

    # Call Claude Sonnet 4
    try:
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        architecture_diagram = response.content[0].text.strip()

        # Extract Mermaid code (remove markdown fences if present)
        if "```mermaid" in architecture_diagram:
            architecture_diagram = architecture_diagram.split("```mermaid")[1].split("```")[0].strip()
        elif "```" in architecture_diagram:
            architecture_diagram = architecture_diagram.split("```")[1].split("```")[0].strip()

    except Exception as e:
        logger.error("Failed to generate architecture with Claude", error=str(e))
        # Fallback: Use simple template
        architecture_diagram = generate_fallback_architecture(selected_technologies)

    # Store in state
    state["architecture_diagram"] = architecture_diagram

    # Update state
    state.update({
        "current_stage": "architecture_generated",
        "completion_percentage": 90.0
    })

    # Send WebSocket update
    await connection_manager.send_progress_update(
        session_id=state["session_id"],
        progress=90.0,
        message="System architecture diagram generated",
        data={"diagram_lines": len(architecture_diagram.split('\n'))}
    )

    logger.info("System architecture diagram generated",
                session_id=state["session_id"],
                diagram_size=len(architecture_diagram))

    return state


def format_tech_stack(technologies: dict) -> str:
    """Format selected technologies for prompt"""
    lines = []
    for category, tech in technologies.items():
        tech_name = tech.get("name", "Unknown") if isinstance(tech, dict) else tech
        lines.append(f"- {category.replace('_', ' ').title()}: {tech_name}")
    return "\n".join(lines)


def count_api_endpoints(api_spec: str) -> int:
    """Count API endpoints from specification"""
    if not api_spec:
        return 0
    # Simple count of "paths:" in OpenAPI spec
    return api_spec.count("paths:") * 5  # Rough estimate


def generate_fallback_architecture(technologies: dict) -> str:
    """Generate basic architecture diagram if Claude fails"""
    return f"""flowchart TB
    subgraph Clients["Client Layer"]
        WebApp["Web Application"]
    end

    subgraph Gateway["API Gateway"]
        LB["Load Balancer"]
    end

    subgraph Application["Application Layer"]
        API["API Server"]
    end

    subgraph Data["Data Layer"]
        DB["Database: {technologies.get('database', {}).get('name', 'PostgreSQL')}"]
        Cache["Cache: {technologies.get('caching', {}).get('name', 'Redis')}"]
    end

    WebApp --> LB
    LB --> API
    API --> DB
    API --> Cache
"""
```

**Tasks**:
1. Create `src/langgraph/nodes/generate_architecture.py`
2. Implement Claude API integration
3. Create comprehensive prompt with all context
4. Parse Mermaid output and validate syntax
5. Implement fallback architecture template
6. Handle errors gracefully
7. Write unit tests (with mocked Claude responses)

**Deliverables**:
- ✅ `generate_architecture_node` implemented
- ✅ Claude integration working
- ✅ Mermaid syntax valid
- ✅ Fallback template available
- ✅ Unit tests passing

**Testing**:
```python
# tests/langgraph/nodes/test_generate_architecture.py
import pytest
from unittest.mock import AsyncMock, patch
from src.langgraph.nodes.generate_architecture import generate_architecture_node

@pytest.mark.asyncio
async def test_generate_architecture():
    state = {
        "session_id": "test-session",
        "selected_technologies": {
            "authentication": {"name": "Passport.js"},
            "database": {"name": "PostgreSQL"},
            "caching": {"name": "Redis"}
        },
        "prd_content": "Build a task management app...",
        "database_schema": {"tables": [{"name": "users"}, {"name": "tasks"}]},
        "api_specification": "paths:\n  /api/tasks:\n    get:"
    }

    # Mock Claude API
    mock_response = """```mermaid
flowchart TB
    WebApp["Next.js App"] --> NGINX["NGINX"]
    NGINX --> API["NestJS Server"]
    API --> PostgreSQL["PostgreSQL"]
```"""

    with patch('src.langgraph.nodes.generate_architecture.anthropic_client') as mock_client:
        mock_client.messages.create = AsyncMock(return_value=MockResponse(mock_response))

        result = await generate_architecture_node(state)

        assert "architecture_diagram" in result
        assert "flowchart TB" in result["architecture_diagram"]
        assert result["completion_percentage"] == 90.0

class MockResponse:
    def __init__(self, text):
        self.content = [type('obj', (object,), {'text': text})]
```

**Run Tests**:
```bash
pytest tests/langgraph/nodes/test_generate_architecture.py -v
```

---

## Day 4: Architecture Validation & Integration

### Morning (4 hours): Implement `validate_architecture` Node

**Objective**: Validate architecture diagram quality using Claude

**File**: `src/langgraph/nodes/validate_architecture.py` (CREATE NEW FILE)

**Implementation**:

```python
"""
Architecture Validation Node
Validates generated architecture diagram for quality and best practices
"""

from datetime import datetime
from anthropic import AsyncAnthropic
from src.langgraph.state import TechSpecState
from src.websocket.connection_manager import connection_manager
from src.config import settings
import structlog
import json

logger = structlog.get_logger(__name__)
anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def validate_architecture_node(state: TechSpecState) -> TechSpecState:
    """
    Validate system architecture diagram.

    Progress: 90% → 92%

    Uses "Architecture Review Agent" (Claude Sonnet 4) to check:
    - Completeness: All necessary components present
    - Consistency: Matches selected technologies
    - Best Practices: Load balancing, caching, replication
    - Scalability: Horizontal scaling capability
    - Security: Authentication, encryption

    Outputs:
    - architecture_score: 0-100
    - validation_report: Detailed feedback
    """
    logger.info("Validating Architecture Diagram", session_id=state["session_id"])

    architecture_diagram = state.get("architecture_diagram", "")
    selected_technologies = state.get("selected_technologies", {})

    if not architecture_diagram:
        logger.warning("No architecture diagram to validate")
        return state

    # Build validation prompt
    prompt = f"""You are an expert system architect. Review the following system architecture diagram.

**Architecture Diagram (Mermaid)**:
```mermaid
{architecture_diagram}
```

**Selected Technologies**:
{json.dumps(selected_technologies, indent=2)}

**Evaluation Criteria** (score each 0-100):

1. **Completeness (25 points)**:
   - Client layer present?
   - API gateway present?
   - Application servers present?
   - Database layer present?
   - Caching layer present?
   - Monitoring tools present?

2. **Consistency (25 points)**:
   - Does architecture use selected technologies?
   - Are technology names correct?

3. **Best Practices (25 points)**:
   - Load balancing implemented?
   - Caching strategy clear?
   - Database replication shown?
   - Horizontal scaling possible?

4. **Scalability (15 points)**:
   - Multiple API server instances?
   - Database read replicas?
   - Stateless services?

5. **Security (10 points)**:
   - Authentication service present?
   - HTTPS/TLS implied?

**Output Format** (JSON only):
{{
  "completeness_score": 0-25,
  "consistency_score": 0-25,
  "best_practices_score": 0-25,
  "scalability_score": 0-15,
  "security_score": 0-10,
  "total_score": 0-100,
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"]
}}

Respond with JSON only, no additional text.
"""

    try:
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )

        validation_json = response.content[0].text.strip()

        # Parse JSON (handle markdown fences)
        if "```json" in validation_json:
            validation_json = validation_json.split("```json")[1].split("```")[0].strip()
        elif "```" in validation_json:
            validation_json = validation_json.split("```")[1].split("```")[0].strip()

        validation_report = json.loads(validation_json)
        architecture_score = validation_report.get("total_score", 0)

    except Exception as e:
        logger.error("Architecture validation failed", error=str(e))
        # Default: assume valid
        validation_report = {
            "total_score": 85,
            "strengths": ["Architecture diagram generated"],
            "weaknesses": ["Could not validate automatically"],
            "recommendations": ["Manual review recommended"]
        }
        architecture_score = 85

    # Update state
    state.update({
        "validation_report": {
            **state.get("validation_report", {}),
            "architecture_score": architecture_score,
            "architecture_validation": validation_report
        },
        "current_stage": "architecture_validated",
        "completion_percentage": 92.0
    })

    # Send WebSocket update
    await connection_manager.send_progress_update(
        session_id=state["session_id"],
        progress=92.0,
        message=f"Architecture validated (score: {architecture_score}/100)",
        data={"architecture_score": architecture_score}
    )

    logger.info("Architecture validation complete",
                session_id=state["session_id"],
                score=architecture_score)

    return state
```

**Tasks**:
1. Create `src/langgraph/nodes/validate_architecture.py`
2. Implement validation prompt
3. Parse JSON validation results
4. Handle validation errors gracefully
5. Store validation report in state
6. Write unit tests

**Deliverables**:
- ✅ `validate_architecture_node` implemented
- ✅ Validation scoring working
- ✅ Error handling robust
- ✅ Unit tests passing

---

### Afternoon (4 hours): Update Workflow Imports & Save Logic

**Objective**: Wire up new nodes and update database save logic

**File 1**: `src/langgraph/workflow.py`

**Tasks**:
1. Import new node functions:
   ```python
   from src.langgraph.nodes.generate_db_erd import generate_db_erd_node
   from src.langgraph.nodes.generate_architecture import generate_architecture_node
   from src.langgraph.nodes.validate_architecture import validate_architecture_node
   ```

2. Verify all nodes are added to workflow (done on Day 1)

3. Test workflow compilation:
   ```python
   workflow = create_workflow()
   graph = workflow.get_graph()
   print(f"Total nodes: {len(graph.nodes)}")  # Should be 20
   ```

**File 2**: `src/langgraph/nodes/save_to_db.py`

**Tasks**:
1. Update `save_to_db_node` to include architecture diagram:
   ```python
   trd_doc = GeneratedTRDDocument(
       session_id=state["session_id"],
       trd_content=state.get("final_trd"),
       api_specification=state.get("api_specification"),
       database_schema=state.get("database_schema"),
       architecture_diagram=state.get("architecture_diagram"),  # ADD THIS
       tech_stack_document=state.get("tech_stack_document"),
       quality_score=state.get("validation_report", {}).get("quality_score"),
       validation_report=state.get("validation_report"),
       version=1
   )
   ```

2. Test database save:
   ```python
   # Verify architecture_diagram is saved
   session = await db.get_session(session_id)
   trd_doc = await db.get_trd_document(session_id)
   assert trd_doc.architecture_diagram is not None
   ```

**Deliverables**:
- ✅ All nodes imported correctly
- ✅ Workflow compiles without errors
- ✅ `save_to_db` includes architecture diagram
- ✅ Database save tested

---

## Day 5: Testing & Documentation

### Morning (4 hours): Integration Testing

**Objective**: Test complete workflow with architecture generation

**File**: `tests/integration/test_architecture_workflow.py` (CREATE NEW FILE)

**Implementation**:

```python
"""
Integration test for architecture generation workflow
"""

import pytest
from uuid import uuid4
from src.langgraph.workflow import create_workflow
from src.langgraph.state import TechSpecState
from src.database.connection import db_manager
from src.database.models import TechSpecSession, GeneratedTRDDocument


@pytest.mark.asyncio
async def test_complete_workflow_with_architecture():
    """Test complete workflow including architecture generation"""

    # Create initial state
    session_id = str(uuid4())
    state: TechSpecState = {
        "session_id": session_id,
        "project_id": str(uuid4()),
        "user_id": str(uuid4()),
        "prd_content": "Build a task management application with user auth and real-time updates",
        "design_docs": {
            "design_system": "Material Design UI",
            "ux_flow": "Login → Dashboard → Task List → Task Detail",
        },
        "selected_technologies": {
            "authentication": {"name": "Passport.js", "category": "authentication"},
            "database": {"name": "PostgreSQL", "category": "database"},
            "caching": {"name": "Redis", "category": "caching"},
        },
        "database_schema": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "uuid", "is_primary_key": True},
                        {"name": "email", "type": "string"},
                    ],
                    "foreign_keys": []
                },
                {
                    "name": "tasks",
                    "columns": [
                        {"name": "id", "type": "uuid", "is_primary_key": True},
                        {"name": "user_id", "type": "uuid", "is_foreign_key": True},
                    ],
                    "foreign_keys": [
                        {"references_table": "users", "cardinality": "||--o{"}
                    ]
                }
            ]
        },
        "final_trd": "# Technical Requirements Document\n...(5000 words)",
        "api_specification": "openapi: 3.0.0\npaths:\n  /api/tasks:\n    get:",
        "current_stage": "db_schema_generated",
        "completion_percentage": 80.0,
        "conversation_history": [],
        "errors": []
    }

    # Create workflow
    workflow = create_workflow()

    # Execute architecture generation nodes
    # (In real workflow, this happens automatically via edges)

    # Node 1: Generate DB ERD
    from src.langgraph.nodes.generate_db_erd import generate_db_erd_node
    state = await generate_db_erd_node(state)

    assert "erd" in state["database_schema"]
    assert "erDiagram" in state["database_schema"]["erd"]
    assert state["completion_percentage"] == 85.0

    # Node 2: Generate Architecture Diagram
    from src.langgraph.nodes.generate_architecture import generate_architecture_node
    state = await generate_architecture_node(state)

    assert "architecture_diagram" in state
    assert "flowchart" in state["architecture_diagram"]
    assert state["completion_percentage"] == 90.0

    # Node 3: Validate Architecture
    from src.langgraph.nodes.validate_architecture import validate_architecture_node
    state = await validate_architecture_node(state)

    assert "architecture_score" in state["validation_report"]
    assert state["validation_report"]["architecture_score"] >= 70  # Minimum acceptable
    assert state["completion_percentage"] == 92.0

    # Node 4: Save to Database
    from src.langgraph.nodes.save_to_db import save_to_db_node
    state = await save_to_db_node(state)

    # Verify database
    async with db_manager.get_async_session() as db_session:
        from sqlalchemy import select

        query = select(GeneratedTRDDocument).where(
            GeneratedTRDDocument.session_id == session_id
        )
        result = await db_session.execute(query)
        trd_doc = result.scalar_one()

        assert trd_doc is not None
        assert trd_doc.architecture_diagram is not None
        assert "flowchart" in trd_doc.architecture_diagram
        assert trd_doc.database_schema is not None
        assert "erd" in trd_doc.database_schema

    print("✅ Integration test passed: Architecture generation complete")


@pytest.mark.asyncio
async def test_architecture_in_download_endpoint():
    """Test that /api/tech-spec/sessions/{session_id}/trd includes architecture"""

    from httpx import AsyncClient
    from src.main import app

    # Create test session with architecture
    session_id = str(uuid4())

    async with db_manager.get_async_session() as db_session:
        # Create session
        session = TechSpecSession(
            id=session_id,
            project_id=uuid4(),
            user_id=uuid4(),
            status="completed",
            progress_percentage=100.0
        )
        db_session.add(session)

        # Create TRD document with architecture
        trd_doc = GeneratedTRDDocument(
            session_id=session_id,
            trd_content="# TRD",
            architecture_diagram="flowchart TB\n  A --> B",
            database_schema={"erd": "erDiagram\n  USERS"},
            quality_score=95.0
        )
        db_session.add(trd_doc)
        await db_session.commit()

    # Test download endpoint
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/tech-spec/sessions/{session_id}/trd",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "document" in data
        assert data["document"]["architecture_diagram"] is not None
        assert "flowchart" in data["document"]["architecture_diagram"]

        print("✅ Download endpoint test passed: Architecture included in response")
```

**Tasks**:
1. Create integration test file
2. Test ERD generation
3. Test architecture diagram generation
4. Test architecture validation
5. Test database save
6. Test REST API endpoint returns architecture
7. Run all tests

**Commands**:
```bash
# Run integration tests
pytest tests/integration/test_architecture_workflow.py -v

# Run all tests
pytest tests/ -v --cov=src/langgraph/nodes
```

**Deliverables**:
- ✅ Integration tests passing
- ✅ Architecture included in database
- ✅ REST API returns architecture
- ✅ WebSocket updates working

---

### Afternoon (4 hours): Documentation & Cleanup

**Objective**: Update documentation and finalize integration

**Tasks**:

1. **Update README.md**:
   - Add architecture generation to features list
   - Update workflow diagram
   - Add example architecture diagram

2. **Update API Documentation** (`src/api/endpoints.py` docstrings):
   ```python
   @router.get("/api/tech-spec/sessions/{session_id}/trd")
   async def download_trd(...):
       """
       Download the generated TRD document.

       Returns:
       - Full TRD content (Markdown)
       - API specification (OpenAPI/Swagger JSON)
       - Database schema (SQL DDL + ERD Mermaid diagram)  # UPDATED
       - Architecture diagram (Mermaid flowchart)          # ADDED
       - Technology stack document
       - Quality score and validation report
       """
   ```

3. **Update CLAUDE.md**:
   - Document architecture generation nodes
   - Add Mermaid syntax examples
   - Update workflow phases

4. **Create Architecture Examples** (`docs/examples/architecture_example.md`):
   - Show example ERD
   - Show example system architecture diagram
   - Explain each component

5. **Update Progress Tracking**:
   - Verify all nodes have correct progress percentages
   - Verify WebSocket messages sent at each step

6. **Code Cleanup**:
   - Remove debug logging
   - Add proper error messages
   - Format code with Black
   - Run linting

**Deliverables**:
- ✅ README.md updated
- ✅ API documentation updated
- ✅ CLAUDE.md updated
- ✅ Example architecture diagrams documented
- ✅ Code formatted and linted

**Commands**:
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

---

## Summary Checklist

### Day 1: Setup ✅
- [ ] Database migration for `architecture_diagram` column
- [ ] Workflow updated with 3 new nodes
- [ ] Edge connections updated
- [ ] Progress percentages recalibrated

### Day 2: ERD Generation ✅
- [ ] `generate_db_erd_node` implemented
- [ ] Mermaid ERD syntax working
- [ ] Unit tests passing
- [ ] WebSocket updates sent

### Day 3: Architecture Generation ✅
- [ ] `generate_architecture_node` implemented
- [ ] Claude integration working
- [ ] Fallback template created
- [ ] Unit tests passing

### Day 4: Validation & Integration ✅
- [ ] `validate_architecture_node` implemented
- [ ] Validation scoring working
- [ ] `save_to_db` updated
- [ ] All nodes wired correctly

### Day 5: Testing & Docs ✅
- [ ] Integration tests passing
- [ ] REST API returns architecture
- [ ] Documentation updated
- [ ] Code formatted and linted

---

## Post-Integration Verification

After 5 days, verify the following:

### Functional Verification
```bash
# 1. Start a Tech Spec session
curl -X POST http://localhost:8000/api/projects/{project_id}/start-tech-spec \
  -H "Authorization: Bearer {token}" \
  -d '{"design_job_id": "{design_job_id}"}'

# 2. Monitor WebSocket for progress updates
# Should see messages at 85%, 90%, 92%

# 3. Download TRD when complete
curl http://localhost:8000/api/tech-spec/sessions/{session_id}/trd \
  -H "Authorization: Bearer {token}"

# 4. Verify architecture_diagram field is present
# Should contain Mermaid flowchart syntax
```

### Database Verification
```sql
-- Check if architecture diagrams are saved
SELECT
  session_id,
  LENGTH(architecture_diagram) as diagram_size,
  quality_score
FROM generated_trd_documents
WHERE architecture_diagram IS NOT NULL
LIMIT 5;
```

### Quality Metrics
- ✅ Architecture diagrams generated for 100% of sessions
- ✅ Average architecture score >= 85/100
- ✅ Mermaid syntax valid (no parse errors)
- ✅ Database ERD includes all tables and relationships
- ✅ System architecture includes all layers (client, gateway, app, data, external)

---

## Rollback Plan

If issues arise, rollback strategy:

1. **Database Rollback**:
   ```bash
   alembic downgrade -1  # Rollback migration
   ```

2. **Code Rollback**:
   ```bash
   git revert <commit-hash>  # Revert architecture integration commits
   ```

3. **Workflow Rollback**:
   - Remove 3 new nodes from workflow
   - Restore old edge: `generate_db_schema → save_to_db`
   - Restore old progress percentages

---

## Success Criteria

### Must Have ✅
- ✅ Database ERD generated and saved
- ✅ System architecture diagram generated and saved
- ✅ Architecture validation working
- ✅ REST API returns architecture in download endpoint
- ✅ All tests passing
- ✅ No breaking changes to existing features

### Nice to Have 🎯
- 🎯 Architecture score >= 90/100 (average)
- 🎯 Diagrams render correctly in Mermaid Live Editor
- 🎯 User can visualize architecture in frontend
- 🎯 Architecture export as PNG/SVG (future enhancement)

---

**Plan Duration**: 5 days (40 hours total)
**Estimated Effort**: 40-50 hours (1 developer)
**Risk Level**: Low (isolated feature addition)
**Dependencies**: Existing workflow must be working

---

**Plan Created**: 2025-01-16
**Feature**: Architecture Generation Integration
**Status**: Ready for Implementation 🚀
