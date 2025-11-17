"""
LangGraph workflow definition for Tech Spec Agent.

Complete 19-node workflow with conditional edges for technology research,
user interaction, clarification, conflict resolution, document generation,
and persistence.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from src.langgraph.state import TechSpecState

# Import all node functions
from src.langgraph.nodes.load_inputs import load_inputs_node
from src.langgraph.nodes.analysis_nodes import (
    analyze_completeness_node,
    ask_user_clarification_node,
    identify_tech_gaps_node,
    warn_user_node
)
from src.langgraph.nodes.research_nodes import (
    research_technologies_node,
    present_options_node,
    wait_user_decision_node,
    validate_decision_node
)
from src.langgraph.nodes.code_analysis_nodes import (
    parse_ai_studio_code_node,
    infer_api_spec_node
)
from src.langgraph.nodes.generation_nodes import (
    generate_trd_node,
    validate_trd_node,
    generate_api_spec_node,
    generate_db_schema_node,
    generate_db_erd_node,
    generate_architecture_node,
    validate_architecture_node,
    generate_tech_stack_doc_node
)
from src.langgraph.nodes.persistence_nodes import (
    save_to_db_node,
    notify_next_agent_node
)


def create_tech_spec_workflow(checkpointer: PostgresSaver = None) -> StateGraph:
    """
    Create Tech Spec Agent LangGraph workflow with 21 nodes and 8 conditional branches.

    **Workflow Structure:**

    Phase 1: Input & Analysis (0-25%)
    - load_inputs → analyze_completeness → identify_tech_gaps

    Phase 2: Technology Research & Selection (25-50%)
    - research_technologies → present_options → wait_user_decision
    - validate_decision → (loop back if more decisions needed)

    Phase 3: Code Analysis (50-65%)
    - parse_ai_studio_code → infer_api_spec

    Phase 4: Document Generation (65-100%)
    - generate_trd → validate_trd (70-75%) → generate_api_spec (80%)
    - generate_db_schema (85%) → generate_db_erd (85%)
    - generate_architecture (90%) → validate_architecture (92%)
    - generate_tech_stack_doc (95%) → save_to_db (98%)
    - notify_next_agent → END (100%)

    **Conditional Branches:**
    1. Completeness check: If score < 80 → ask_user_clarification
    2. Tech gaps: If no gaps found → skip research, go to code parsing
    3. Options to present: If more decisions needed → loop back to present_options
    4. Decision validation: If conflicts found → warn_user
    5. After warning: User decides → reselect or proceed
    6. TRD validation: If score < 90 and iterations < 3 → regenerate
    7. All decisions complete: Continue to code analysis
    8. All complete: → save and notify next agent

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence (optional)

    Returns:
        Compiled StateGraph ready for execution
    """
    workflow = StateGraph(TechSpecState)

    # =========================================================================
    # 1. Add all 21 nodes
    # =========================================================================

    # Phase 1: Input & Analysis
    workflow.add_node("load_inputs", load_inputs_node)
    workflow.add_node("analyze_completeness", analyze_completeness_node)
    workflow.add_node("ask_user_clarification", ask_user_clarification_node)
    workflow.add_node("identify_tech_gaps", identify_tech_gaps_node)

    # Phase 2: Technology Research
    workflow.add_node("research_technologies", research_technologies_node)
    workflow.add_node("present_options", present_options_node)
    workflow.add_node("wait_user_decision", wait_user_decision_node)
    workflow.add_node("validate_decision", validate_decision_node)
    workflow.add_node("warn_user", warn_user_node)

    # Phase 3: Code Analysis
    workflow.add_node("parse_ai_studio_code", parse_ai_studio_code_node)
    workflow.add_node("infer_api_spec", infer_api_spec_node)

    # Phase 4: Document Generation
    workflow.add_node("generate_trd", generate_trd_node)
    workflow.add_node("validate_trd", validate_trd_node)
    workflow.add_node("generate_api_spec", generate_api_spec_node)
    workflow.add_node("generate_db_schema", generate_db_schema_node)
    workflow.add_node("generate_db_erd", generate_db_erd_node)
    workflow.add_node("generate_architecture", generate_architecture_node)
    workflow.add_node("validate_architecture", validate_architecture_node)
    workflow.add_node("generate_tech_stack_doc", generate_tech_stack_doc_node)

    # Phase 5: Persistence & Notification
    workflow.add_node("save_to_db", save_to_db_node)
    workflow.add_node("notify_next_agent", notify_next_agent_node)

    # =========================================================================
    # 2. Define workflow edges and conditional branches
    # =========================================================================

    # Entry point
    workflow.set_entry_point("load_inputs")

    # Phase 1: Input & Analysis
    workflow.add_edge("load_inputs", "analyze_completeness")

    # Branch 1: Check completeness score
    workflow.add_conditional_edges(
        "analyze_completeness",
        _check_completeness_score,
        {
            "needs_clarification": "ask_user_clarification",  # Score < 80
            "sufficient": "identify_tech_gaps"                 # Score >= 80
        }
    )

    # User clarification → re-analyze or continue
    workflow.add_edge("ask_user_clarification", "identify_tech_gaps")

    # Branch 2: Check if technology gaps exist
    workflow.add_conditional_edges(
        "identify_tech_gaps",
        _check_tech_gaps_exist,
        {
            "has_gaps": "research_technologies",      # Research needed
            "no_gaps": "parse_ai_studio_code"        # Skip to code analysis
        }
    )

    # Phase 2: Technology Research (with loop for multiple decisions)
    workflow.add_edge("research_technologies", "present_options")

    # Branch 2: Check if there are options to present
    workflow.add_conditional_edges(
        "present_options",
        _check_options_to_present,
        {
            "has_options": "wait_user_decision",       # Wait for user choice
            "no_options": "parse_ai_studio_code"      # All decided, proceed
        }
    )

    workflow.add_edge("wait_user_decision", "validate_decision")

    # Branch 3: Check for decision conflicts
    workflow.add_conditional_edges(
        "validate_decision",
        _check_decision_conflicts,
        {
            "has_conflicts": "warn_user",              # Warn user about conflicts
            "no_conflicts": "present_options"          # Continue to next decision
        }
    )

    # After warning, user can reselect or proceed
    workflow.add_edge("warn_user", "present_options")
    # Note: present_options will check if more decisions needed

    # Phase 3: Code Analysis (linear flow)
    workflow.add_edge("parse_ai_studio_code", "infer_api_spec")
    workflow.add_edge("infer_api_spec", "generate_trd")

    # Phase 4: Document Generation
    workflow.add_edge("generate_trd", "validate_trd")

    # Branch 4: TRD validation with retry logic
    workflow.add_conditional_edges(
        "validate_trd",
        _check_trd_quality,
        {
            "valid": "generate_api_spec",              # TRD passed validation
            "invalid_retry": "generate_trd",           # Regenerate (< 3 attempts)
            "invalid_force_pass": "generate_api_spec"  # Force pass after 3 attempts
        }
    )

    # Remaining document generation (linear flow)
    workflow.add_edge("generate_api_spec", "generate_db_schema")
    workflow.add_edge("generate_db_schema", "generate_db_erd")
    workflow.add_edge("generate_db_erd", "generate_architecture")
    workflow.add_edge("generate_architecture", "validate_architecture")
    workflow.add_edge("validate_architecture", "generate_tech_stack_doc")

    # Phase 5: Persistence & Notification
    workflow.add_edge("generate_tech_stack_doc", "save_to_db")
    workflow.add_edge("save_to_db", "notify_next_agent")
    workflow.add_edge("notify_next_agent", END)

    # =========================================================================
    # 3. Compile workflow with checkpointer
    # =========================================================================

    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled


# =============================================================================
# Conditional edge functions
# =============================================================================

def _check_completeness_score(state: TechSpecState) -> str:
    """
    Branch 1: Check if completeness score is sufficient.

    Returns:
        - "needs_clarification": Score < 80, need to ask user questions
        - "sufficient": Score >= 80, proceed with workflow
    """
    completeness_score = state.get("completeness_score", 0)
    return "needs_clarification" if completeness_score < 80 else "sufficient"


def _check_tech_gaps_exist(state: TechSpecState) -> str:
    """
    Branch 2: Check if technology gaps were identified.

    Returns:
        - "has_gaps": Technology decisions need to be made
        - "no_gaps": All technologies already specified, skip research
    """
    identified_gaps = state.get("identified_gaps", [])
    return "has_gaps" if len(identified_gaps) > 0 else "no_gaps"


def _check_options_to_present(state: TechSpecState) -> str:
    """
    Branch 3: Check if there are more options to present to user.

    Returns:
        - "has_options": There's a category to present
        - "no_options": All decisions made, proceed to code analysis
    """
    # Check if there are pending decisions
    pending = state.get("pending_decisions", [])

    # Check if current research category is set
    current_category = state.get("current_research_category")

    # Check if all identified gaps have user decisions
    identified_gaps = state.get("identified_gaps", [])
    user_decisions = state.get("user_decisions", [])
    decided_categories = {d.get("category") for d in user_decisions}
    gap_categories = {g.get("category") for g in identified_gaps}

    all_decided = gap_categories.issubset(decided_categories)

    if all_decided and not pending and not current_category:
        return "no_options"

    return "has_options"


def _check_decision_conflicts(state: TechSpecState) -> str:
    """
    Branch 4: Check if user's technology decision has conflicts.

    Returns:
        - "has_conflicts": Warning issued, user may want to reconsider
        - "no_conflicts": Decision validated successfully
    """
    # Check if validation warnings were generated
    warnings = state.get("decision_warnings", [])

    # Critical conflicts should loop back
    critical_conflicts = [w for w in warnings if w.get("severity") == "critical"]

    return "has_conflicts" if len(critical_conflicts) > 0 else "no_conflicts"


def _check_trd_quality(state: TechSpecState) -> str:
    """
    Branch 4: Check TRD validation quality with retry logic.

    Returns:
        - "valid": TRD score >= 90, proceed
        - "invalid_retry": TRD score < 90, retry count < 3
        - "invalid_force_pass": TRD score < 90, retry count >= 3 (give up)
    """
    validation_result = state.get("trd_validation", {})
    total_score = validation_result.get("total_score", 0.0)
    iteration_count = state.get("iteration_count", 0)

    PASS_THRESHOLD = 90.0
    MAX_RETRIES = 3

    if total_score >= PASS_THRESHOLD:
        return "valid"

    if iteration_count < MAX_RETRIES:
        return "invalid_retry"

    # Force pass after max retries
    return "invalid_force_pass"
