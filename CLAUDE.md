# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tech Spec Agent** is a LangGraph-based AI agent that serves as a critical bridge between design and development in the ANYON development workflow. It automatically generates detailed Technical Requirements Documents (TRD) by analyzing PRD and design documents, researching appropriate technologies, and inferring API specifications from code.

**Position in ANYON Workflow:**
```
선-기획 Agent → 후-기획 Agent → 디자인 Agent
    → [Tech Spec Agent] ← YOU ARE HERE
    → 백로그 Agent → 계획 Agent → 개발 Agent → ...
```

**Core Responsibilities:**
- Validate completeness of PRD and design documents
- Identify technology gaps and research open-source solutions
- Present technology options to users with pros/cons analysis
- Parse Google AI Studio generated code to infer API specifications
- Generate comprehensive technical documentation (TRD, API specs, DB schemas, architecture diagrams)

## Architecture

### LangGraph State Machine (19 Nodes, 5 Conditional Branches)

**4-Phase Structure:**

1. **Phase 1: Input & Analysis (0-25%)**
   - `load_inputs`: Load PRD, design docs from PostgreSQL
   - `analyze_completeness`: Evaluate completeness (0-100 score)
   - `ask_user_clarification`: Ask questions if score < 80
   - `identify_tech_gaps`: Detect undecided technical choices

2. **Phase 2: Technology Research & Selection (25-50%)**
   - `research_technologies`: Web search for open-source libraries
   - `present_options`: Show 3 options with pros/cons/metrics
   - `wait_user_decision`: Wait for user selection via WebSocket
   - `validate_decision`: Check for conflicts with requirements
   - `warn_user`: Display warnings if conflicts detected
   - **Loops until all gaps resolved**

3. **Phase 3: Code Analysis (50-65%)**
   - `parse_ai_studio_code`: Parse Google AI Studio ZIP file
   - `infer_api_spec`: Infer API endpoints from React components

4. **Phase 4: Document Generation (65-100%)**
   - `generate_trd`: Create main TRD document
   - `validate_trd`: Verify quality (>= 90 score, max 3 retries)
   - `generate_api_spec`: OpenAPI YAML specification
   - `generate_db_schema`: SQL DDL with ERD
   - `generate_architecture`: Mermaid diagrams
   - `generate_tech_stack_doc`: Technology stack documentation
   - `save_to_db`: Persist all documents to PostgreSQL
   - `notify_next_agent`: Trigger backlog agent

### Conditional Branches

1. **Completeness Check**: If score < 80 → ask user clarification
2. **Gap Existence**: If no gaps → skip to code parsing
3. **Validation Conflict**: If conflicts → show warning
4. **User Reselection**: Allow reselection if conflicts
5. **Pending Decisions**: Loop Phase 2 until all gaps resolved
6. **TRD Validation**: Retry generation if quality < 90 (max 3x)

### State Schema

```python
class TechSpecState(TypedDict):
    # Session
    session_id: str
    project_id: str
    user_id: str

    # Inputs
    prd_content: str
    design_docs: Dict[str, str]  # 5 design document types
    initial_trd: str
    google_ai_studio_code_path: Optional[str]

    # Analysis
    completeness_score: float  # 0-100
    missing_elements: List[str]
    ambiguous_elements: List[str]

    # Technology Gaps
    technical_gaps: List[Dict]
    tech_research_results: Annotated[List[Dict], operator.add]
    selected_technologies: Dict[str, Dict]
    pending_decisions: List[str]

    # Conversation
    current_question: Optional[str]
    conversation_history: Annotated[List[Dict], operator.add]

    # Code Analysis
    google_ai_studio_data: Optional[Dict]
    inferred_api_spec: Optional[Dict]

    # Generated Documents
    trd_draft: str
    trd_validation_result: Dict  # {score, gaps, recommendations}
    api_specification: str
    database_schema: str
    architecture_diagram: str
    tech_stack_document: str

    # Meta
    current_stage: str
    completion_percentage: float  # 0-100
    iteration_count: int
    errors: Annotated[List[Dict], operator.add]
```

## Database Schema

### Core Tables

**tech_spec_sessions**
- Tracks each Tech Spec Agent session
- Links to project, PRD, and design documents
- Stores completeness scores and current stage

**tech_research**
- Stores technology research results for each gap
- Contains options (JSONB), selected option, selection reason
- Links research to specific sessions

**tech_conversations**
- Preserves all agent-user interactions
- Enables replay and debugging
- Links messages to related research

**generated_trd_documents**
- Stores all 5 document types with versioning
- Includes validation scores
- Supports rollback to previous versions

## Key Technologies

### Must Use
- **Language**: TypeScript (Node.js backend), Python (LangGraph)
- **Framework**: NestJS (API), Next.js 14 (Frontend)
- **AI Orchestration**: LangGraph with checkpointing
- **LLM**: Claude Sonnet 4 (claude-sonnet-4-20250514)
- **Database**: PostgreSQL 14+ with Prisma ORM
- **Real-time**: WebSocket (Socket.io)
- **Storage**: AWS S3 for Google AI Studio ZIP files

### Code Patterns

**LangGraph Node Implementation:**
```python
async def node_name_node(state: TechSpecState) -> TechSpecState:
    """
    Brief description

    - Purpose 1
    - Purpose 2
    """
    # Implementation

    # Update state
    state.update({
        "field": value,
        "current_stage": "stage_name",
        "completion_percentage": 50.0
    })

    # Add conversation message
    state["conversation_history"].append({
        "role": "agent",
        "message": "User-facing message",
        "timestamp": datetime.now()
    })

    return state
```

**Error Handling:**
```python
async def handle_node_error(node_name: str, error: Exception, state: TechSpecState) -> TechSpecState:
    """
    Handle errors with graceful degradation
    """
    state["errors"].append({
        "node": node_name,
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.now()
    })

    # Provide fallback or retry logic
    # Log to database for monitoring

    return state
```

**WebSocket Communication:**
```typescript
// Server → Client progress updates
{
  "type": "progress_update" | "agent_message" | "completion",
  "sessionId": "uuid",
  "progress": 0-100,
  "message": "...",
  "data": {...}
}

// Client → Server user input
{
  "type": "user_message",
  "sessionId": "uuid",
  "message": "1" | "2" | "3" | "AI 추천" | "검색: <tech>",
  "context": {...}
}
```

## Development Commands

### Running the Agent

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Run database migrations
npx prisma migrate dev

# Start development servers
npm run dev          # Frontend (Next.js)
npm run dev:api      # Backend API (NestJS)
python agent.py      # LangGraph agent

# Run tests
npm test
pytest tests/
```

### Database Operations

```bash
# Create migration
npx prisma migrate dev --name migration_name

# Reset database
npx prisma migrate reset

# Open Prisma Studio
npx prisma studio
```

### Testing Workflow

```bash
# Test single node
pytest tests/nodes/test_research_technologies.py -v

# Test full workflow
pytest tests/workflows/test_tech_spec_complete.py -v

# Test WebSocket communication
npm run test:websocket
```

## Important Implementation Notes

### Web Search Integration
- Use `web_search` tool for discovering open-source technologies
- Always fetch top 5 candidates, present top 3 to user
- Search pattern: `"{category} {language} library 2025 comparison"`
- Extract: GitHub stars, npm downloads, pros/cons, use cases

### Google AI Studio Code Parsing
- Parse TypeScript AST to extract components
- Look for patterns:
  - `fetch()` and `axios.*()` calls for API endpoints
  - Props interfaces for response types
  - Event handlers for request triggers
- Infer API specs: component → endpoint mapping
- Handle missing code gracefully (fallback to PRD/design only)

### Document Generation Quality
- TRD must score >= 90 on validation
- Retry generation max 3 times if quality insufficient
- Check for:
  - Completeness: All required sections present
  - Consistency: Matches PRD and selected technologies
  - Clarity: No ambiguous terminology
  - Actionability: Developers can start immediately

### User Experience
- Progress updates every node transition
- Clear, non-technical language for option presentation
- Emoji usage for visual clarity (⭐ for recommendation, ✅/❌ for pros/cons)
- "AI 추천" option always available
- Allow custom tech search with "검색: <tech name>"

### Performance Optimization
- Cache web search results (15 min TTL)
- Stream large document generation to frontend
- Parallel research for multiple gaps when possible
- Use checkpointing for session resumability

## Critical Paths

### Happy Path (No Issues)
```
load_inputs → analyze_completeness (score >= 80)
→ identify_tech_gaps → research (for each gap)
→ present → wait_decision → validate
→ parse_ai_studio_code → infer_api
→ generate_trd (pass validation)
→ generate_api/db/arch/tech docs → save → notify
```

### With User Clarification
```
analyze_completeness (score < 80)
→ ask_user_clarification → re-analyze → proceed
```

### With Validation Conflict
```
validate_decision (conflict found)
→ warn_user → user chooses reselect or continue
```

### With TRD Quality Issues
```
validate_trd (score < 90, iteration < 3)
→ regenerate_trd → validate again
```

## Success Metrics

- **Completion Rate**: 95% of started sessions complete successfully
- **Average Duration**: 15-25 minutes for 5 technology decisions
- **User Satisfaction**: 4.5/5.0 rating
- **TRD Quality**: 90/100 average validation score
- **Technology Retention**: 85% of selected technologies remain in final implementation

## Common Issues & Solutions

**Issue**: Web search returns no results
- **Solution**: Use predefined technology templates for common categories (auth, database, file storage)

**Issue**: Google AI Studio code parsing fails
- **Solution**: Skip code analysis, infer API specs from PRD and design documents only

**Issue**: User disconnects mid-session
- **Solution**: Use LangGraph checkpointing to resume from last state when user returns

**Issue**: TRD validation fails 3 times
- **Solution**: Force pass with warning, flag for human review

**Issue**: Technology conflict detected
- **Solution**: Show detailed warning with severity (critical/warning), allow user override

## Future Enhancements

1. **Caching Layer**: Redis for research results to reduce web search calls
2. **Parallel Gap Research**: Research multiple technology gaps simultaneously
3. **AI-Driven Recommendations**: Train model on past successful selections
4. **Code Template Generation**: Generate boilerplate code for selected tech stack
5. **Integration Testing**: Verify technology compatibility automatically
