"""
LangGraph state schema for Tech Spec Agent workflow.
Defines the complete state structure for all 17 nodes.
"""

from typing import TypedDict, List, Dict, Optional, Annotated
import operator


class TechSpecState(TypedDict):
    """
    State schema for Tech Spec Agent workflow.
    Based on Tech_Spec_Agent_LangGraph_Detailed.md

    Uses Annotated[List, operator.add] for list fields that accumulate
    across nodes (conversation history, research results, etc.)
    """

    # ============= Session Metadata =============
    session_id: str
    project_id: str
    user_id: str
    design_job_id: str  # Foreign key to Design Agent

    # ============= Input Data from Design Agent =============
    prd_content: str
    design_docs: Dict[str, str]  # {doc_type: content}
    ai_studio_code_path: str
    design_decisions: List[Dict]  # Design Agent user decisions

    # ============= Analysis Results =============
    completeness_score: float  # 0-100
    identified_gaps: List[Dict]  # [{category, description, priority, required}]
    gap_count: int

    # ============= Technology Research =============
    # Accumulates research results across multiple categories
    research_results: Annotated[List[Dict], operator.add]
    # {category: [options]} - Current options for presentation
    technology_options: Dict[str, List[Dict]]
    # Accumulates user decisions
    user_decisions: Annotated[List[Dict], operator.add]
    # Current category being researched
    current_research_category: str
    # Decision validation warnings
    decision_warnings: List[Dict]
    # Clarification questions for user
    clarification_questions: List[Dict]

    # ============= Code Analysis =============
    parsed_components: List[Dict]  # [{name, type, props, state, apis}]
    inferred_apis: List[Dict]  # [{endpoint, method, params, response}]
    code_analysis_summary: Dict

    # ============= Document Generation =============
    trd_draft: str
    trd_validation_result: Dict  # {score, gaps, recommendations}
    api_specification: str  # OpenAPI/Swagger JSON
    database_schema: str  # SQL DDL statements
    architecture_diagram: str  # Mermaid diagram code
    tech_stack_document: str  # Markdown document

    # ============= Workflow Control =============
    current_stage: str  # Current node name
    iteration_count: int  # For TRD regeneration
    max_iterations: int  # Max TRD generation attempts
    paused: bool  # True when waiting for user decision
    completed: bool  # True when workflow finished

    # ============= Progress Tracking =============
    progress_percentage: float  # 0-100
    pending_decisions: int
    completed_decisions: int
    total_decisions: int

    # ============= Error Handling =============
    # Accumulates errors across nodes
    errors: Annotated[List[Dict], operator.add]  # [{node, error_type, message, timestamp}]
    retry_count: Dict[str, int]  # {node_name: retry_count}

    # ============= Conversation History =============
    # Accumulates all conversation messages
    conversation_history: Annotated[List[Dict], operator.add]
    # [{role, message, timestamp, metadata}]

    # ============= Metadata =============
    started_at: str  # ISO timestamp
    updated_at: str  # ISO timestamp
    completed_at: Optional[str]  # ISO timestamp


def create_initial_state(
    session_id: str,
    project_id: str,
    user_id: str,
    design_job_id: str,
) -> TechSpecState:
    """
    Create initial state for a new Tech Spec session.

    Args:
        session_id: UUID of the Tech Spec session
        project_id: UUID of the project
        user_id: UUID of the user
        design_job_id: UUID of the Design Agent job

    Returns:
        Initial state with default values
    """
    from datetime import datetime

    now = datetime.now().isoformat()

    return TechSpecState(
        # Session metadata
        session_id=session_id,
        project_id=project_id,
        user_id=user_id,
        design_job_id=design_job_id,
        # Input data (to be loaded)
        prd_content="",
        design_docs={},
        ai_studio_code_path="",
        design_decisions=[],
        # Analysis results
        completeness_score=0.0,
        identified_gaps=[],
        gap_count=0,
        # Technology research
        research_results=[],
        technology_options={},
        user_decisions=[],
        current_research_category="",
        decision_warnings=[],
        clarification_questions=[],
        # Code analysis
        parsed_components=[],
        inferred_apis=[],
        code_analysis_summary={},
        # Document generation
        trd_draft="",
        trd_validation_result={},
        api_specification="",
        database_schema="",
        architecture_diagram="",
        tech_stack_document="",
        # Workflow control
        current_stage="load_inputs",
        iteration_count=0,
        max_iterations=3,
        paused=False,
        completed=False,
        # Progress tracking
        progress_percentage=0.0,
        pending_decisions=0,
        completed_decisions=0,
        total_decisions=0,
        # Error handling
        errors=[],
        retry_count={},
        # Conversation history
        conversation_history=[],
        # Metadata
        started_at=now,
        updated_at=now,
        completed_at=None,
    )
