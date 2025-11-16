"""
Analysis nodes for Tech Spec Agent workflow.
Includes completeness analysis and technology gap identification.
"""

from typing import Dict, List
import structlog
from datetime import datetime
import json

from src.langgraph.state import TechSpecState
from src.llm.client import LLMClient, ModelType, Message

logger = structlog.get_logger(__name__)


async def analyze_completeness_node(state: TechSpecState) -> TechSpecState:
    """
    Analyze completeness of PRD and design documents.

    Evaluates whether the provided documents contain enough information
    to generate a comprehensive Technical Requirements Document.

    Scoring criteria (0-100):
    - Authentication & authorization specification (0-10)
    - API endpoints defined (0-20)
    - Data models clarity (0-20)
    - File handling specification (0-10)
    - Real-time features specification (0-10)
    - External integrations specification (0-10)
    - Error handling policies (0-10)
    - Security requirements (0-5)
    - Performance requirements (0-3)
    - Deployment environment (0-2)

    Args:
        state: Current workflow state with PRD and design docs

    Returns:
        Updated state with completeness score and identified gaps
    """
    logger.info(
        "Analyzing completeness",
        session_id=state["session_id"]
    )

    try:
        # Create LLM client (uses settings.anthropic_model from .env)
        llm = LLMClient(temperature=0.3)

        # Prepare analysis prompt
        analysis_prompt = f"""Analyze the following PRD and design documents to evaluate completeness for technical specification.

PRD Content:
{state['prd_content'][:5000]}  # Limit to 5000 chars to avoid token limit

Design Documents:
{_format_design_docs(state['design_docs'])[:5000]}

Evaluate these criteria and provide scores (0-100 total):

1. Authentication & Authorization (0-10 points):
   - Are auth methods specified?
   - Are user roles defined?
   - Are permission models clear?

2. API Endpoints (0-20 points):
   - Are API endpoints listed?
   - Are request/response formats defined?
   - Are HTTP methods specified?

3. Data Models (0-20 points):
   - Are database entities defined?
   - Are relationships specified?
   - Are field types clear?

4. File Handling (0-10 points):
   - Are file upload/download requirements specified?
   - Are storage solutions mentioned?
   - Are file size limits defined?

5. Real-time Features (0-10 points):
   - Are WebSocket/SSE requirements specified?
   - Are real-time data flows defined?

6. External Integrations (0-10 points):
   - Are third-party APIs listed?
   - Are integration requirements clear?

7. Error Handling (0-10 points):
   - Are error handling patterns defined?
   - Are fallback strategies mentioned?

8. Security (0-5 points):
   - Are security requirements specified?
   - Are encryption needs mentioned?

9. Performance (0-3 points):
   - Are performance targets defined?
   - Are load requirements specified?

10. Deployment (0-2 points):
    - Is deployment environment mentioned?

Respond with JSON:
{{
    "total_score": <0-100>,
    "scores": {{
        "authentication": <0-10>,
        "api_endpoints": <0-20>,
        "data_models": <0-20>,
        "file_handling": <0-10>,
        "realtime": <0-10>,
        "external_integrations": <0-10>,
        "error_handling": <0-10>,
        "security": <0-5>,
        "performance": <0-3>,
        "deployment": <0-2>
    }},
    "missing_elements": [
        {{"category": "...", "description": "...", "impact": "high|medium|low"}}
    ],
    "ambiguous_elements": [
        {{"category": "...", "description": "...", "clarification_needed": "..."}}
    ],
    "recommendations": [
        "..."
    ]
}}"""

        # Generate analysis
        result = await llm.generate_json(
            messages=[Message(role="user", content=analysis_prompt)],
            system="You are a technical requirements analyst. Evaluate documentation completeness objectively and provide actionable feedback.",
            temperature=0.3,
            max_tokens=2048
        )

        # Update state
        state.update({
            "completeness_score": result["total_score"],
            "current_stage": "analyze_completeness",
            "progress_percentage": 15.0,
            "updated_at": datetime.now().isoformat()
        })

        # Store metadata
        state["conversation_history"].append({
            "role": "agent",
            "message": _format_completeness_message(result),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "analyze_completeness",
                "scores": result["scores"],
                "total_score": result["total_score"]
            }
        })

        logger.info(
            "Completeness analysis complete",
            session_id=state["session_id"],
            total_score=result["total_score"],
            missing_count=len(result.get("missing_elements", [])),
            ambiguous_count=len(result.get("ambiguous_elements", []))
        )

        return state

    except Exception as e:
        logger.error(
            "Completeness analysis failed",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "analyze_completeness",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Set conservative score on error
        state["completeness_score"] = 50.0

        raise


async def identify_tech_gaps_node(state: TechSpecState) -> TechSpecState:
    """
    Identify technology gaps that need user decisions.

    Analyzes PRD and design docs to find areas where specific technology
    choices are needed but not yet specified. These will be researched
    and presented to the user for decision.

    Common technology categories:
    - Authentication (OAuth, JWT, sessions)
    - Database (SQL, NoSQL, ORM)
    - File storage (S3, Cloudinary, local)
    - Frontend framework/library
    - Backend framework
    - Real-time communication (WebSockets, SSE)
    - Payment processing
    - Email service
    - Caching layer

    Args:
        state: Current workflow state

    Returns:
        Updated state with identified technology gaps
    """
    logger.info(
        "Identifying technology gaps",
        session_id=state["session_id"]
    )

    try:
        llm = LLMClient(temperature=0.3)

        # Prepare gap identification prompt
        gap_prompt = f"""Analyze the following project requirements and identify technology choices that need to be made.

PRD:
{state['prd_content'][:5000]}

Design Documents:
{_format_design_docs(state['design_docs'])[:5000]}

Identify technology gaps in these categories:
1. Authentication & Authorization
2. Database & ORM
3. File Storage
4. Frontend Framework/Libraries
5. Backend Framework
6. Real-time Communication
7. Payment Processing (if needed)
8. Email Service (if needed)
9. Caching Layer
10. API Documentation
11. Testing Frameworks
12. CI/CD Pipeline

For each gap, determine:
- Is a technology choice mentioned in the documents?
- If not, is it required based on the features?
- What is the priority (critical, high, medium, low)?

Respond with JSON:
{{
    "technology_gaps": [
        {{
            "category": "<category_name>",
            "description": "Brief description of what needs to be decided",
            "why_needed": "Why this technology is needed for the project",
            "priority": "critical|high|medium|low",
            "suggested_options": ["option1", "option2", "option3"],
            "decision_impact": "What parts of the system this affects"
        }}
    ],
    "already_specified": [
        {{
            "category": "<category_name>",
            "technology": "<specified_tech>",
            "source": "Where it was specified in the documents"
        }}
    ],
    "total_gaps": <count>,
    "critical_gaps": <count>,
    "estimated_research_time": "<time_estimate>"
}}"""

        # Generate gap analysis
        result = await llm.generate_json(
            messages=[Message(role="user", content=gap_prompt)],
            system="You are a technology stack consultant. Identify missing technology decisions that are critical for project implementation.",
            temperature=0.3,
            max_tokens=3072
        )

        # Update state
        gaps = result.get("technology_gaps", [])
        pending_categories = [
            gap.get("category")
            for gap in gaps
            if gap.get("category")
        ]
        state.update({
            "identified_gaps": gaps,
            "gap_count": len(gaps),
            "total_decisions": len(gaps),
            "pending_decisions": pending_categories,
            "completed_decisions": 0,
            "current_stage": "identify_tech_gaps",
            "progress_percentage": 25.0,
            "updated_at": datetime.now().isoformat()
        })

        # Add conversation message
        state["conversation_history"].append({
            "role": "agent",
            "message": _format_gaps_message(result),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "identify_tech_gaps",
                "total_gaps": len(gaps),
                "critical_gaps": result.get("critical_gaps", 0)
            }
        })

        logger.info(
            "Technology gaps identified",
            session_id=state["session_id"],
            total_gaps=len(gaps),
            critical_gaps=result.get("critical_gaps", 0)
        )

        return state

    except Exception as e:
        logger.error(
            "Gap identification failed",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "identify_tech_gaps",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        raise


# ============= Helper Functions =============

def _format_design_docs(design_docs: Dict[str, str]) -> str:
    """Format design docs for LLM prompt."""
    formatted = []
    for doc_type, content in design_docs.items():
        if content:
            formatted.append(f"## {doc_type.upper()}\n{content[:1000]}")  # Limit each doc
    return "\n\n".join(formatted)


def _format_completeness_message(result: Dict) -> str:
    """Format completeness analysis result for user."""
    score = result["total_score"]

    if score >= 80:
        emoji = "✅"
        status = "EXCELLENT"
    elif score >= 60:
        emoji = "⚠️"
        status = "GOOD"
    else:
        emoji = "❌"
        status = "NEEDS IMPROVEMENT"

    message = f"""{emoji} **Completeness Analysis: {status}** (Score: {score}/100)

**Breakdown:**
- Authentication: {result['scores']['authentication']}/10
- API Endpoints: {result['scores']['api_endpoints']}/20
- Data Models: {result['scores']['data_models']}/20
- File Handling: {result['scores']['file_handling']}/10
- Real-time: {result['scores']['realtime']}/10
- External Integrations: {result['scores']['external_integrations']}/10
- Error Handling: {result['scores']['error_handling']}/10
- Security: {result['scores']['security']}/5
- Performance: {result['scores']['performance']}/3
- Deployment: {result['scores']['deployment']}/2

"""

    if result.get("missing_elements"):
        message += "\n**Missing Elements:**\n"
        for elem in result["missing_elements"][:5]:  # Top 5
            message += f"- {elem['description']} (Impact: {elem['impact']})\n"

    if result.get("recommendations"):
        message += "\n**Recommendations:**\n"
        for rec in result["recommendations"][:3]:  # Top 3
            message += f"- {rec}\n"

    return message


def _format_gaps_message(result: Dict) -> str:
    """Format technology gaps result for user."""
    total_gaps = result.get("total_gaps", 0)
    critical_gaps = result.get("critical_gaps", 0)

    message = f"""📋 **Technology Gap Analysis Complete**

Found **{total_gaps} technology decisions** that need to be made ({critical_gaps} critical).

"""

    if result.get("already_specified"):
        message += "✅ **Already Specified:**\n"
        for spec in result["already_specified"][:3]:
            message += f"- {spec['category']}: {spec['technology']}\n"
        message += "\n"

    if result.get("technology_gaps"):
        message += "🔍 **Needs Research & Decision:**\n"
        for gap in result["technology_gaps"][:5]:  # Top 5
            priority_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(gap["priority"], "⚪")

            message += f"{priority_emoji} **{gap['category']}**: {gap['description']}\n"

    message += f"\nStarting technology research for all {total_gaps} gaps..."

    return message


async def ask_user_clarification_node(state: TechSpecState) -> TechSpecState:
    """
    Ask user for clarification when completeness score < 80.

    This node pauses the workflow and presents specific questions to the user
    about missing or ambiguous elements in the PRD/design documents.

    The workflow resumes when the user provides answers via the API.

    Args:
        state: Current workflow state with completeness analysis results

    Returns:
        Updated state with pause flag and clarification questions
    """
    logger.info(
        "Asking user for clarification",
        session_id=state["session_id"],
        completeness_score=state.get("completeness_score", 0)
    )

    try:
        llm = LLMClient(temperature=0.3)

        # Generate specific clarification questions based on missing elements
        # Extract missing/ambiguous elements from completeness analysis
        # (These would be stored during analyze_completeness_node)

        clarification_prompt = f"""Based on the completeness analysis (score: {state.get('completeness_score', 0)}/100),
generate 3-5 specific clarification questions to ask the user about missing or ambiguous requirements.

PRD Summary:
{state['prd_content'][:2000]}

Focus on the most critical missing elements that would prevent generating a complete TRD.

Respond with JSON:
{{
    "questions": [
        {{
            "category": "<category>",
            "question": "<specific question>",
            "why_needed": "<why this is critical>",
            "examples": ["example answer 1", "example answer 2"]
        }}
    ],
    "estimated_time": "<time to answer>"
}}"""

        result = await llm.generate_json(
            messages=[Message(role="user", content=clarification_prompt)],
            system="You are a requirements analyst. Generate clear, specific questions that will help fill gaps in the technical specification.",
            temperature=0.3,
            max_tokens=2048
        )

        # Store clarification questions in state
        state.update({
            "paused": True,
            "current_stage": "ask_user_clarification",
            "progress_percentage": 18.0,
            "updated_at": datetime.now().isoformat(),
            "clarification_questions": result.get("questions", [])
        })

        # Format message for user
        questions_text = "\n\n".join([
            f"**Q{i+1}: {q['category']}**\n{q['question']}\n_Why needed: {q['why_needed']}_"
            for i, q in enumerate(result.get("questions", []))
        ])

        state["conversation_history"].append({
            "role": "agent",
            "message": f"""⚠️ **Clarification Needed** (Completeness: {state.get('completeness_score', 0)}/100)

The provided documents are missing some critical information. Please answer the following questions to help generate a complete Technical Requirements Document:

{questions_text}

Please provide your answers, and I'll continue with the technical specification.""",
            "timestamp": datetime.now().isoformat(),
            "message_type": "clarification_request",
            "metadata": {
                "node": "ask_user_clarification",
                "question_count": len(result.get("questions", []))
            }
        })

        logger.info(
            "Clarification questions prepared",
            session_id=state["session_id"],
            question_count=len(result.get("questions", []))
        )

        return state

    except Exception as e:
        logger.error(
            "Failed to generate clarification questions",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "ask_user_clarification",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Skip clarification on error, proceed with what we have
        state["paused"] = False

        raise


async def warn_user_node(state: TechSpecState) -> TechSpecState:
    """
    Warn user about technology decision conflicts.

    This node is triggered when validate_decision detects that a user's
    technology choice conflicts with project requirements or other decisions.

    The user can then:
    1. Reselect a different technology
    2. Proceed anyway with understanding of the conflict
    3. Provide additional context

    Args:
        state: Current workflow state with decision warnings

    Returns:
        Updated state with warning message and pause flag
    """
    logger.info(
        "Warning user about decision conflicts",
        session_id=state["session_id"]
    )

    try:
        # Get decision warnings from state
        # (These would be set by validate_decision_node)
        warnings = state.get("decision_warnings", [])

        if not warnings:
            logger.warning(
                "warn_user_node called but no warnings found",
                session_id=state["session_id"]
            )
            return state

        # Format warnings for display
        warnings_text = "\n\n".join([
            f"**⚠️ {w.get('severity', 'WARNING').upper()}**: {w.get('category', 'Unknown')}\n"
            f"{w.get('message', 'Conflict detected')}\n"
            f"_Impact: {w.get('impact', 'May cause integration issues')}_\n"
            f"_Recommendation: {w.get('recommendation', 'Consider alternative')}_"
            for w in warnings
        ])

        # Pause workflow for user response
        state.update({
            "paused": True,
            "current_stage": "warn_user",
            "progress_percentage": state.get("progress_percentage", 45.0),
            "updated_at": datetime.now().isoformat()
        })

        # Add warning message to conversation
        state["conversation_history"].append({
            "role": "agent",
            "message": f"""⚠️ **Technology Decision Conflict Detected**

{warnings_text}

**What would you like to do?**
1. **Reselect** - Choose a different technology
2. **Proceed Anyway** - Continue with this choice (risks noted)
3. **Provide Context** - Explain why this choice is appropriate

Please respond with your decision.""",
            "timestamp": datetime.now().isoformat(),
            "message_type": "conflict_warning",
            "metadata": {
                "node": "warn_user",
                "warning_count": len(warnings),
                "severity": max(w.get("severity", "warning") for w in warnings)
            }
        })

        logger.info(
            "User warned about conflicts",
            session_id=state["session_id"],
            warning_count=len(warnings)
        )

        return state

    except Exception as e:
        logger.error(
            "Failed to warn user",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "warn_user",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # On error, proceed without warning (don't block workflow)
        state["paused"] = False

        raise
