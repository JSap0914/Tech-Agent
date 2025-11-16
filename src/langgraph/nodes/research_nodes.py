"""
Technology research nodes for Tech Spec Agent workflow.
Handles researching, presenting, and collecting user decisions on technology choices.
"""

from typing import Dict, List, Optional, Awaitable, Callable
import asyncio
import structlog
from datetime import datetime
import json
import hashlib

from src.langgraph.state import TechSpecState
from src.research.tech_research import TechnologyResearcher, ResearchResult
from src.config import settings
from src.cache import redis_client

logger = structlog.get_logger(__name__)


async def research_technologies_node(state: TechSpecState) -> TechSpecState:
    """
    Research technology options for all identified gaps.

    Uses Tavily API to search for open-source libraries and frameworks
    for each technology category that needs a decision.

    Args:
        state: Current workflow state with identified gaps

    Returns:
        Updated state with research results
    """
    logger.info(
        "Researching technologies",
        session_id=state["session_id"],
        total_gaps=len(state["identified_gaps"])
    )

    try:
        researcher = TechnologyResearcher()

        # Prepare context for research (shared across all gaps)
        context = {
            "project_type": _infer_project_type(state),
            "tech_stack": _extract_tech_stack(state),
            "requirements": state["prd_content"][:1000]  # Snippet for context
        }

        # Helper function to research a single gap with cache check
        async def _research_single_gap(gap: Dict) -> Dict:
            """Research a single technology gap with caching."""
            try:
                # Week 12: Check cache first to avoid redundant API calls
                cache_key = _generate_research_cache_key(gap["category"], context)
                cached_result = await redis_client.get(cache_key)

                if cached_result:
                    logger.info(
                        "Using cached research results",
                        category=gap["category"],
                        cache_key=cache_key
                    )
                    return cached_result

                # Research this technology category (cache miss)
                result = await researcher.research_category(
                    category=gap["category"],
                    question=gap["description"],
                    context=context,
                    max_options=settings.tech_spec_max_options_per_gap
                )

                research_data = {
                    "gap_id": gap.get("id", gap["category"]),
                    "category": gap["category"],
                    "description": gap["description"],
                    "priority": gap.get("priority", "medium"),
                    "options": [opt.dict() for opt in result.options],
                    "summary": result.research_summary,
                    "recommendation": result.recommendation
                }

                # Week 12: Cache the research results (24 hour TTL)
                await redis_client.set(
                    cache_key,
                    research_data,
                    ttl=settings.tech_spec_cache_ttl
                )

                logger.info(
                    "Research completed for category",
                    category=gap["category"],
                    options_found=len(result.options),
                    cached=True
                )

                return research_data

            except Exception as e:
                logger.error(
                    "Failed to research gap",
                    category=gap.get("category", "unknown"),
                    error=str(e)
                )
                # Return error placeholder instead of failing entire workflow
                return {
                    "gap_id": gap.get("id", gap["category"]),
                    "category": gap["category"],
                    "description": gap["description"],
                    "priority": gap.get("priority", "medium"),
                    "options": [],
                    "summary": f"Research failed: {str(e)}",
                    "recommendation": "Manual selection required",
                    "error": str(e)
                }

        # PARALLEL PROCESSING: Research all gaps concurrently
        logger.info("Starting parallel research", gap_count=len(state["identified_gaps"]))
        research_tasks = [_research_single_gap(gap) for gap in state["identified_gaps"]]
        research_results = await asyncio.gather(*research_tasks, return_exceptions=True)

        # Filter out any exception results and log them
        valid_results = []
        for i, result in enumerate(research_results):
            if isinstance(result, Exception):
                logger.error(
                    "Research task failed with exception",
                    gap_index=i,
                    error=str(result)
                )
                # Add fallback error result
                gap = state["identified_gaps"][i]
                valid_results.append({
                    "gap_id": gap.get("id", gap["category"]),
                    "category": gap["category"],
                    "description": gap["description"],
                    "priority": gap.get("priority", "medium"),
                    "options": [],
                    "summary": f"Research failed: {str(result)}",
                    "recommendation": "Manual selection required",
                    "error": str(result)
                })
            else:
                valid_results.append(result)

        research_results = valid_results

        # Update state
        state["research_results"].extend(research_results)

        # Set current research category to first unresolved gap
        if research_results:
            state["current_research_category"] = research_results[0]["category"]

        state.update({
            "current_stage": "research_technologies",
            "progress_percentage": 35.0,
            "updated_at": datetime.now().isoformat()
        })

        # Add conversation message
        state["conversation_history"].append({
            "role": "agent",
            "message": f"✅ Completed research for {len(research_results)} technology categories. Ready to present options...",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "research_technologies",
                "research_count": len(research_results)
            }
        })

        logger.info(
            "Technology research complete",
            session_id=state["session_id"],
            categories_researched=len(research_results)
        )

        return state

    except Exception as e:
        logger.error(
            "Technology research failed",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "research_technologies",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        raise


async def present_options_node(state: TechSpecState) -> TechSpecState:
    """
    Present technology options to user for the next undecided gap.

    Formats research results into user-friendly questions with
    clear pros/cons for each option.

    Args:
        state: Current workflow state with research results

    Returns:
        Updated state with formatted question for user
    """
    logger.info(
        "Presenting technology options",
        session_id=state["session_id"]
    )

    try:
        # Find next undecided research category
        decided_categories = {decision["category"] for decision in state["user_decisions"]}
        next_research = None

        for research in state["research_results"]:
            if research["category"] not in decided_categories:
                next_research = research
                break

        if not next_research:
            # All decisions made
            state.update({
                "paused": False,
                "current_stage": "present_options",
                "progress_percentage": 50.0,
                "updated_at": datetime.now().isoformat()
            })

            state["conversation_history"].append({
                "role": "agent",
                "message": "✅ All technology decisions have been made! Proceeding to code analysis...",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "node": "present_options",
                    "all_decided": True
                }
            })

            return state

        # Ensure options exist (fallback to PRD suggestions if needed)
        fallback_used = False
        if not next_research.get("options"):
            gap_info = _find_gap_by_category(
                state.get("identified_gaps", []),
                next_research["category"]
            )
            next_research["options"] = _build_fallback_options(
                category=next_research["category"],
                gap=gap_info,
                error_message=next_research.get("error")
            )
            fallback_used = True

        if not next_research["options"]:
            logger.error(
                "No technology options available after fallback",
                session_id=state["session_id"],
                category=next_research["category"]
            )
            raise RuntimeError(
                f"No technology options available for {next_research['category']}."
            )

        # Format options for presentation - Skip in CLI mode to save memory
        # The formatted message is ~10-50KB per category and was being stored in state
        # CLI mode displays options directly via terminal_ui, doesn't need this message
        # message = _format_options_message(next_research)  # Commented out for memory optimization

        # Update state
        tech_options = dict(state.get("technology_options", {}))
        tech_options[next_research["category"]] = next_research["options"]
        state.update({
            "current_research_category": next_research["category"],
            "technology_options": tech_options,
            "paused": True,  # Wait for user decision
            "current_stage": "present_options",
            "progress_percentage": 40.0 + (state["completed_decisions"] / state["total_decisions"] * 10),
            "updated_at": datetime.now().isoformat()
        })

        # Add conversation message
        if fallback_used and not next_research.get("_fallback_logged"):
            state["conversation_history"].append({
                "role": "agent",
                "message": (
                    f"⚠️ Automated research for {next_research['category']} "
                    "was unavailable (rate limit or API error). Showing fallback "
                    "options derived from the initial requirements so you can "
                    "continue making decisions."
                ),
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "node": "present_options",
                    "category": next_research["category"],
                    "fallback": True
                }
            })
            next_research["_fallback_logged"] = True

        # Store only lightweight summary in conversation_history to save memory
        # Full details are already in state["research_results"] and state["technology_options"]
        state["conversation_history"].append({
            "role": "agent",
            "message": f"🔍 Presenting technology options for {next_research['category']} ({len(next_research['options'])} options available)",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "present_options",
                "category": next_research["category"],
                "options_count": len(next_research["options"])
            }
        })

        logger.info(
            "Options presented to user",
            session_id=state["session_id"],
            category=next_research["category"],
            options_count=len(next_research["options"]),
            fallback_used=fallback_used
        )

        return state

    except Exception as e:
        logger.error(
            "Failed to present options",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "present_options",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        raise


async def wait_user_decision_node(state: TechSpecState) -> TechSpecState:
    """
    Wait for user to make a technology decision.

    This is a checkpoint node that pauses the workflow until
    the user submits their decision via the API.

    Args:
        state: Current workflow state

    Returns:
        State (unchanged - waiting for external input)
    """
    category = state.get("current_research_category")
    options = state.get("technology_options", {}).get(category, []) if category else []

    logger.info(
        "Waiting for user decision",
        session_id=state["session_id"],
        category=category,
        options_count=len(options)
    )

    if not options:
        logger.error(
            "No technology options available while waiting for user decision",
            session_id=state["session_id"],
            category=category
        )
        raise RuntimeError(
            f"No technology options available for {category}. "
            "Workflow cannot continue."
        )

    # If a decision callback was registered (CLI execution), wait for it
    if _user_decision_callback:
        await _user_decision_callback(state)
        state.update({
            "paused": False,
            "current_stage": "wait_user_decision",
            "updated_at": datetime.now().isoformat()
        })
        return state

    # Default behaviour (API/async workflow): mark as paused and return
    state.update({
        "paused": True,
        "current_stage": "wait_user_decision",
        "updated_at": datetime.now().isoformat()
    })

    return state


async def validate_decision_node(state: TechSpecState) -> TechSpecState:
    """
    Validate user's technology decision for conflicts.

    Checks if the selected technology is compatible with:
    - Project requirements
    - Already selected technologies
    - Design constraints

    Args:
        state: Current workflow state with user decision

    Returns:
        Updated state with validation results
    """
    logger.info(
        "Validating technology decision",
        session_id=state["session_id"]
    )

    try:
        # Get latest decision
        if not state["user_decisions"]:
            # No decision to validate
            return state

        latest_decision = state["user_decisions"][-1]

        # Check for conflicts
        conflicts = _check_technology_conflicts(
            latest_decision,
            state["user_decisions"][:-1],  # Previous decisions
            state["prd_content"]
        )

        if conflicts:
            # Add warning to conversation
            warning_message = _format_conflicts_warning(
                latest_decision,
                conflicts
            )

            state["conversation_history"].append({
                "role": "agent",
                "message": warning_message,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "node": "validate_decision",
                    "has_conflicts": True,
                    "conflicts": conflicts
                }
            })

            logger.warning(
                "Technology decision has conflicts",
                session_id=state["session_id"],
                category=latest_decision["category"],
                conflicts_count=len(conflicts)
            )
        else:
            # Decision is valid
            state["conversation_history"].append({
                "role": "agent",
                "message": f"✅ **{latest_decision['technology_name']}** is a great choice for {latest_decision['category']}!",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "node": "validate_decision",
                    "has_conflicts": False
                }
            })

            logger.info(
                "Technology decision validated",
                session_id=state["session_id"],
                category=latest_decision["category"],
                technology=latest_decision["technology_name"]
            )

        # Update counters
        decided_categories = {
            decision.get("category")
            for decision in state["user_decisions"]
            if decision.get("category")
        }
        pending_categories = [
            gap.get("category")
            for gap in state.get("identified_gaps", [])
            if gap.get("category") and gap.get("category") not in decided_categories
        ]

        state.update({
            "completed_decisions": len(state["user_decisions"]),
            "pending_decisions": pending_categories,
            "paused": False,  # Continue workflow
            "current_stage": "validate_decision",
            "updated_at": datetime.now().isoformat()
        })

        return state

    except Exception as e:
        logger.error(
            "Decision validation failed",
            session_id=state["session_id"],
            error=str(e)
        )

        state["errors"].append({
            "node": "validate_decision",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Continue anyway - validation is not critical
        state["paused"] = False
        return state


# ============= Helper Functions =============

def _infer_project_type(state: TechSpecState) -> str:
    """Infer project type from PRD content."""
    prd = state["prd_content"].lower()

    if "mobile" in prd or "ios" in prd or "android" in prd:
        return "mobile application"
    elif "web" in prd or "website" in prd or "webapp" in prd:
        return "web application"
    elif "api" in prd or "backend" in prd:
        return "API/backend service"
    elif "desktop" in prd:
        return "desktop application"
    else:
        return "web application"  # Default


def _extract_tech_stack(state: TechSpecState) -> Dict[str, str]:
    """Extract already decided technology stack from user decisions."""
    tech_stack = {}

    for decision in state["user_decisions"]:
        tech_stack[decision["category"]] = decision["technology_name"]

    return tech_stack


def _generate_research_cache_key(category: str, context: Dict) -> str:
    """
    Generate cache key for technology research results.

    Week 12: Performance optimization - cache research results to avoid redundant API calls.

    Args:
        category: Technology category (e.g., "authentication", "database")
        context: Research context (project_type, tech_stack, requirements)

    Returns:
        Cache key for Redis
    """
    # Create deterministic hash of context
    context_str = json.dumps({
        "project_type": context.get("project_type", ""),
        "tech_stack": context.get("tech_stack", {}),
        "requirements_hash": hashlib.md5(
            context.get("requirements", "").encode()
        ).hexdigest()[:8]
    }, sort_keys=True)

    context_hash = hashlib.md5(context_str.encode()).hexdigest()[:12]

    return f"tech_research:{category}:{context_hash}"


def _find_gap_by_category(gaps: List[Dict], category: str) -> Optional[Dict]:
    """Locate identified gap dictionary by category."""
    for gap in gaps:
        if gap.get("category") == category:
            return gap
    return None


def _build_fallback_options(
    category: str,
    gap: Optional[Dict],
    error_message: Optional[str]
) -> List[Dict]:
    """
    Build fallback technology options when automated research fails.

    Uses suggested options from the PRD/identified gaps so the user can continue
    making selections without needing fresh LLM output.
    """
    suggestions = (gap or {}).get("suggested_options", []) or [f"Custom {category} option"]
    description = (gap or {}).get(
        "description",
        f"Manually evaluate candidate technologies for {category}."
    )
    fallback_options: List[Dict] = []

    for idx, name in enumerate(suggestions[:3]):
        fallback_options.append({
            "technology_name": name,
            "description": description,
            "pros": [
                "Originated from initial project requirements or team preferences",
                "Can be evaluated manually despite automated research limits"
            ],
            "cons": [
                "Detailed research unavailable in current run"
                + (f" ({error_message})" if error_message else ""),
                "Requires manual validation for scalability, cost, and integration"
            ],
            "use_cases": [
                f"{category} needs for the current project scope"
            ],
            "popularity_score": max(30.0, 60.0 - (idx * 5)),
            "learning_curve": "medium",
            "documentation_quality": "unknown",
            "community_support": "unknown",
            "integration_complexity": "medium",
            "sources": [],
            "recommended": idx == 0,
            "metrics": {
                "github_stars": "N/A",
                "npm_downloads": "N/A",
                "last_update": "N/A"
            }
        })

    return fallback_options


def _format_options_message(research: Dict) -> str:
    """Format technology options into user-friendly message."""
    category = research["category"]
    description = research["description"]
    options = research["options"]
    recommendation = research.get("recommendation", "")

    message = f"""🔍 **{category.upper()}**

{description}

"""

    # Add summary if available
    if research.get("summary"):
        message += f"{research['summary']}\n\n"

    # Add options
    message += "**Options:**\n\n"

    for i, option in enumerate(options, 1):
        message += f"""**{i}. {option['technology_name']}**
{option['description']}

✅ **Pros:**
{_format_list(option['pros'])}

❌ **Cons:**
{_format_list(option['cons'])}

📊 **Metrics:**
- Popularity: {option['popularity_score']}/100
- Learning Curve: {option['learning_curve']}
- Documentation: {option['documentation_quality']}
- Integration Complexity: {option['integration_complexity']}

💡 **Use Cases:**
{_format_list(option['use_cases'])}

---

"""

    # Add recommendation if available
    if recommendation:
        message += f"\n💡 **AI Recommendation:**\n{recommendation}\n\n"

    message += """**What would you like to choose?**
- Reply with the number (1, 2, or 3)
- Or type "AI recommendation" to go with the suggested option
- Or type "search" to manually enter a different technology
"""

    return message


def _format_list(items: List[str]) -> str:
    """Format list of items as bullet points."""
    return "\n".join([f"- {item}" for item in items])


def _check_technology_conflicts(
    decision: Dict,
    previous_decisions: List[Dict],
    prd_content: str
) -> List[Dict]:
    """
    Check for conflicts between selected technology and other factors.

    Returns list of conflict dictionaries with severity and description.
    """
    conflicts = []

    # Example conflict checks (simplified)
    # In production, this would use LLM to analyze compatibility

    technology = decision["technology_name"].lower()
    category = decision["category"]

    # Check against previous decisions
    for prev_decision in previous_decisions:
        prev_tech = prev_decision["technology_name"].lower()

        # Example: MongoDB + relational-heavy requirements
        if "mongo" in technology and "postgresql" in prev_tech:
            conflicts.append({
                "severity": "medium",
                "description": f"Mixing MongoDB ({category}) with PostgreSQL ({prev_decision['category']}) adds complexity",
                "suggestion": "Consider using PostgreSQL for all data storage"
            })

    return conflicts


def _format_conflicts_warning(decision: Dict, conflicts: List[Dict]) -> str:
    """Format conflicts warning message."""
    message = f"""⚠️ **Potential Conflicts Detected**

Your selection of **{decision['technology_name']}** for {decision['category']} may have some compatibility concerns:

"""

    for i, conflict in enumerate(conflicts, 1):
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(conflict["severity"], "⚪")

        message += f"""{severity_emoji} **Conflict {i}** (Severity: {conflict['severity']})
- {conflict['description']}
- Suggestion: {conflict['suggestion']}

"""

    message += """You can:
1. Continue with this selection anyway
2. Choose a different option
3. Get more details about the conflicts
"""

    return message
UserDecisionCallback = Optional[Callable[[TechSpecState], Awaitable[None]]]
_user_decision_callback: UserDecisionCallback = None


def register_user_decision_callback(callback: UserDecisionCallback) -> None:
    """
    Allow external runners (e.g., CLI) to inject an async handler that collects
    user decisions before the workflow continues past wait_user_decision.
    """
    global _user_decision_callback
    _user_decision_callback = callback
