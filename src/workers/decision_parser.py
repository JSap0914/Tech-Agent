"""
User decision parser for WebSocket messages.

Parses incoming user decisions from WebSocket and converts them into
structured format for workflow resumption.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class UserDecision(BaseModel):
    """Structured user decision for technology selection."""

    category: str = Field(..., description="Technology gap category (e.g., 'authentication', 'database')")
    selected_technology: str = Field(..., description="Name of selected technology")
    reasoning: Optional[str] = Field(None, description="User's reasoning for selection")
    confidence: str = Field("medium", description="User confidence level: low, medium, high")
    custom_requirements: Optional[Dict] = Field(None, description="Additional custom requirements")


async def parse_user_decision(message: Dict, context: Optional[Dict] = None) -> UserDecision:
    """
    Parse user decision from WebSocket message.

    Args:
        message: Raw WebSocket message from client
        context: Optional context about the decision (current state, available options, etc.)

    Returns:
        UserDecision object with parsed data

    Raises:
        ValueError: If required fields are missing or invalid

    Example:
        >>> message = {
        ...     "type": "user_decision",
        ...     "category": "authentication",
        ...     "technologyName": "NextAuth.js",
        ...     "reasoning": "Best for Next.js projects"
        ... }
        >>> decision = await parse_user_decision(message)
        >>> decision.selected_technology
        'NextAuth.js'
    """
    # Extract required fields
    category = message.get("category")
    technology_name = message.get("technologyName")

    if not category:
        raise ValueError("Missing required field: 'category'")

    if not technology_name:
        raise ValueError("Missing required field: 'technologyName'")

    # Extract optional fields
    reasoning = message.get("reasoning", "")
    confidence = message.get("confidence", "medium")
    custom_requirements = message.get("customRequirements")

    # Validate confidence level
    if confidence not in ["low", "medium", "high"]:
        logger.warning(
            "invalid_confidence_level",
            provided=confidence,
            defaulting_to="medium"
        )
        confidence = "medium"

    # Create structured decision
    decision = UserDecision(
        category=category,
        selected_technology=technology_name,
        reasoning=reasoning or None,
        confidence=confidence,
        custom_requirements=custom_requirements
    )

    logger.info(
        "decision_parsed",
        category=decision.category,
        technology=decision.selected_technology,
        confidence=decision.confidence
    )

    return decision


def validate_decision_against_context(decision: UserDecision, context: Optional[Dict]) -> tuple[bool, Optional[str]]:
    """
    Validate user decision against available options and requirements.

    Args:
        decision: Parsed user decision
        context: Context with available options and requirements

    Returns:
        Tuple of (is_valid, error_message)
            - is_valid: True if decision is valid
            - error_message: None if valid, error description if invalid

    Example:
        >>> decision = UserDecision(category="database", selected_technology="MongoDB")
        >>> context = {"available_options": ["PostgreSQL", "MySQL", "MongoDB"]}
        >>> is_valid, error = validate_decision_against_context(decision, context)
        >>> is_valid
        True
    """
    if not context:
        # No context to validate against - accept decision
        return True, None

    # Check if selected technology is in available options
    available_options = context.get("available_options", [])

    if available_options and decision.selected_technology not in available_options:
        return False, f"'{decision.selected_technology}' is not in available options: {available_options}"

    # Check if decision meets minimum requirements
    min_reasoning_length = context.get("min_reasoning_length", 0)

    if min_reasoning_length > 0 and (not decision.reasoning or len(decision.reasoning) < min_reasoning_length):
        return False, f"Reasoning must be at least {min_reasoning_length} characters"

    # All validations passed
    return True, None
