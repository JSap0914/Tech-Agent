"""
Document generation nodes for Tech Spec Agent workflow.
Generates TRD, API spec, database schema, architecture diagrams.
"""

from typing import Dict, List, Tuple
import re
import structlog
from datetime import datetime

from src.langgraph.state import TechSpecState
from src.llm.client import LLMClient, ModelType, Message
from src.config import settings

logger = structlog.get_logger(__name__)


async def generate_trd_node(state: TechSpecState) -> TechSpecState:
    """
    Generate Technical Requirements Document (TRD).

    Creates comprehensive TRD based on:
    - Original PRD
    - Design documents
    - User technology decisions
    - Inferred API specifications
    - Code analysis results

    Args:
        state: Current workflow state with all inputs and decisions

    Returns:
        Updated state with TRD draft
    """
    logger.info(
        "Generating TRD",
        session_id=state["session_id"],
        iteration=state["iteration_count"]
    )

    try:
        llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.5)

        # Build TRD generation prompt
        prompt = _build_trd_prompt(state)

        # Generate TRD
        messages = [Message(role="user", content=prompt)]
        response = await llm.generate(
            messages=messages,
            system="You are a senior technical architect creating detailed Technical Requirements Documents. Be comprehensive, specific, and actionable.",
            temperature=0.5,
            max_tokens=8192
        )

        # Update state
        state.update({
            "trd_draft": response.content,
            "iteration_count": state["iteration_count"] + 1,
            "current_stage": "generate_trd",
            "progress_percentage": 70.0,
            "updated_at": datetime.now().isoformat()
        })

        # Add conversation message
        state["conversation_history"].append({
            "role": "agent",
            "message": f"✅ Generated TRD draft ({len(response.content)} characters). Validating quality...",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "generate_trd",
                "iteration": state["iteration_count"],
                "length": len(response.content)
            }
        })

        logger.info(
            "TRD generated successfully",
            session_id=state["session_id"],
            length=len(response.content),
            iteration=state["iteration_count"]
        )

        return state

    except Exception as e:
        logger.error("TRD generation failed", session_id=state["session_id"], error=str(e))

        state["errors"].append({
            "node": "generate_trd",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        raise


async def validate_trd_node(state: TechSpecState) -> TechSpecState:
    """
    Validate TRD quality and completeness.

    Scores TRD on:
    - Completeness (all sections present)
    - Clarity (unambiguous language)
    - Actionability (developers can implement immediately)
    - Consistency (matches PRD and decisions)

    Threshold: >= 90/100 to pass

    Args:
        state: Current workflow state with TRD draft

    Returns:
        Updated state with validation results
    """
    logger.info(
        "Validating TRD",
        session_id=state["session_id"]
    )

    try:
        # Step 1: Programmatic structure validation
        trd_content = state.get("trd_draft", "")
        structure_valid, structure_issues, structure_score = _validate_trd_structure(trd_content)

        logger.info(
            "Structure validation complete",
            session_id=state["session_id"],
            structure_score=structure_score,
            structure_valid=structure_valid,
            issues_found=len(structure_issues)
        )

        # If structure validation fails critically, skip LLM validation and fail immediately
        if structure_score < 40:
            logger.warning(
                "TRD structure critically incomplete, skipping LLM validation",
                session_id=state["session_id"],
                structure_score=structure_score
            )

            # Format structure issues for user
            issues_text = "\n".join([
                f"- **{issue['section']}**: {issue['issue']} ({issue['severity']} severity)"
                for issue in structure_issues[:10]  # Limit to top 10 issues
            ])

            state.update({
                "trd_validation_result": {
                    "total_score": structure_score,
                    "structure_score": structure_score,
                    "scores": {
                        "completeness": 0,
                        "clarity": 0,
                        "actionability": 0,
                        "consistency": 0
                    },
                    "gaps": structure_issues,
                    "recommendations": [
                        "Regenerate TRD with all required sections",
                        "Ensure each section has substantial content",
                        "Include code examples and API specifications"
                    ],
                    "pass": False,
                    "structure_validation_failed": True
                },
                "current_stage": "validate_trd",
                "progress_percentage": 75.0,
                "updated_at": datetime.now().isoformat()
            })

            state["conversation_history"].append({
                "role": "agent",
                "message": f"""❌ STRUCTURE VALIDATION FAILED - TRD Quality Score: {structure_score}/100

**Critical Issues Found:**
{issues_text}

The TRD is missing critical sections or has insufficient content. Regenerating...""",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "node": "validate_trd",
                    "score": structure_score,
                    "pass": False,
                    "structure_validation_failed": True
                }
            })

            return state

        # Step 2: LLM-based semantic validation (only if structure passes)
        llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.2)

        # Build validation prompt with structure validation context
        structure_issues_text = "\n".join([
            f"- {issue['section']}: {issue['issue']}"
            for issue in structure_issues[:5]
        ]) if structure_issues else "No structural issues found"

        # Build validation prompt
        validation_prompt = f"""Validate the quality of this Technical Requirements Document (TRD).

**Structure Validation Results:**
- Structure Score: {structure_score}/100
- Structure Valid: {structure_valid}
- Issues Found: {structure_issues_text}

**TRD Content:**
{state['trd_draft'][:10000]}  # Limit to avoid token overflow

**Original PRD:**
{state['prd_content'][:2000]}

**Technology Decisions:**
{_format_tech_decisions(state['user_decisions'])}

**Validation Criteria (Score 0-100 total):**

1. **Completeness (0-30 points):**
   - Are all sections present? (Overview, Tech Stack, Architecture, API Spec, DB Schema, Security, Performance, Deployment)
   - Are all user decisions reflected?
   - Are all PRD requirements addressed?

2. **Clarity (0-25 points):**
   - Is technical language precise and unambiguous?
   - Are acronyms defined?
   - Are diagrams and examples provided?

3. **Actionability (0-25 points):**
   - Can developers start implementation immediately?
   - Are API endpoints fully specified?
   - Are database schemas complete with DDL?

4. **Consistency (0-20 points):**
   - Does TRD match PRD requirements?
   - Are technology choices correctly integrated?
   - Are there no contradictions?

Respond with JSON:
{{
    "total_score": <0-100>,
    "scores": {{
        "completeness": <0-30>,
        "clarity": <0-25>,
        "actionability": <0-25>,
        "consistency": <0-20>
    }},
    "gaps": [
        {{"section": "...", "issue": "...", "severity": "high|medium|low"}}
    ],
    "recommendations": [
        "..."
    ],
    "pass": <true|false>
}}

Pass threshold: total_score >= 90
"""

        # Generate validation
        result = await llm.generate_json(
            messages=[Message(role="user", content=validation_prompt)],
            temperature=0.2,
            max_tokens=2048
        )

        # Step 3: Multi-agent specialized review (only if score is reasonable)
        multi_agent_review = None
        if result.get("total_score", 0) >= 60:  # Only run if basic validation passed
            logger.info(
                "Running multi-agent review",
                session_id=state["session_id"]
            )

            multi_agent_review = await _multi_agent_trd_review(
                trd_content=trd_content,
                prd_content=state.get("prd_content", ""),
                tech_decisions=state.get("user_decisions", [])
            )

            logger.info(
                "Multi-agent review complete",
                session_id=state["session_id"],
                multi_agent_score=multi_agent_review.get("multi_agent_score", 0)
            )

        # Merge structure validation with LLM validation
        # Combine structure issues with LLM-detected gaps
        all_gaps = structure_issues + result.get("gaps", [])

        # Add multi-agent critical issues to gaps if available
        if multi_agent_review:
            for issue in multi_agent_review.get("critical_issues", []):
                all_gaps.append({
                    "section": "Multi-Agent Review",
                    "issue": issue,
                    "severity": "high"
                })

        # Enhance result with structure validation data and multi-agent review
        result["structure_score"] = structure_score
        result["structure_valid"] = structure_valid
        result["gaps"] = all_gaps

        # Add multi-agent review data if available
        if multi_agent_review:
            result["multi_agent_review"] = multi_agent_review
            result["multi_agent_score"] = multi_agent_review.get("multi_agent_score", 0)

        # Update state
        state.update({
            "trd_validation_result": result,
            "current_stage": "validate_trd",
            "progress_percentage": 75.0,
            "updated_at": datetime.now().isoformat()
        })

        # Format structure issues for display (top 3)
        structure_issues_display = ""
        if structure_issues:
            structure_issues_display = "\n\n**Structure Issues:**\n" + "\n".join([
                f"- {issue['section']}: {issue['issue']}"
                for issue in structure_issues[:3]
            ])

        # Format multi-agent review for display
        multi_agent_display = ""
        if multi_agent_review:
            review_summary = multi_agent_review.get("review_summary", {})
            multi_agent_display = f"\n\n**Multi-Agent Review:** {multi_agent_review.get('multi_agent_score', 0):.0f}/100\n"
            multi_agent_display += "\n".join([
                f"- {agent_config['agent_name']}: {agent_config['score']}/100"
                for agent_id, agent_config in review_summary.items()
            ])

            # Show top 3 recommendations
            top_recommendations = multi_agent_review.get("recommendations", [])[:3]
            if top_recommendations:
                multi_agent_display += "\n\n**Key Recommendations:**\n"
                multi_agent_display += "\n".join([f"- {rec}" for rec in top_recommendations])

        # Add conversation message
        pass_status = "✅ PASSED" if result.get("pass", False) else "❌ NEEDS IMPROVEMENT"
        state["conversation_history"].append({
            "role": "agent",
            "message": f"""{pass_status} - TRD Quality Score: {result['total_score']}/100

**Breakdown:**
- Completeness: {result['scores']['completeness']}/30
- Clarity: {result['scores']['clarity']}/25
- Actionability: {result['scores']['actionability']}/25
- Consistency: {result['scores']['consistency']}/20
- Structure: {structure_score}/100 {"✅" if structure_valid else "⚠️"}
{structure_issues_display}
{multi_agent_display}
""",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "validate_trd",
                "score": result['total_score'],
                "structure_score": structure_score,
                "multi_agent_score": multi_agent_review.get("multi_agent_score", 0) if multi_agent_review else None,
                "pass": result.get("pass", False)
            }
        })

        logger.info(
            "TRD validation complete",
            session_id=state["session_id"],
            score=result['total_score'],
            pass_validation=result.get("pass", False)
        )

        return state

    except Exception as e:
        logger.error("TRD validation failed", session_id=state["session_id"], error=str(e))

        state["errors"].append({
            "node": "validate_trd",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Set conservative validation result on error
        state["trd_validation_result"] = {
            "total_score": 50.0,
            "pass": False,
            "error": str(e)
        }

        return state


async def generate_api_spec_node(state: TechSpecState) -> TechSpecState:
    """Generate OpenAPI/Swagger specification."""
    logger.info("Generating API specification", session_id=state["session_id"])

    try:
        llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.3)

        prompt = f"""Generate an OpenAPI 3.0 specification based on the TRD and inferred APIs.

**TRD Content:**
{state['trd_draft'][:5000]}

**Inferred APIs from Code:**
{str(state.get('inferred_apis', []))[:2000]}

**Technology Decisions:**
{_format_tech_decisions(state['user_decisions'])}

Generate a complete OpenAPI 3.0 YAML specification including:
- All endpoints with methods, parameters, request/response schemas
- Authentication schemes
- Error responses
- Examples

Respond with valid YAML only.
"""

        response = await llm.generate(
            messages=[Message(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=6144
        )

        state.update({
            "api_specification": response.content,
            "current_stage": "generate_api_spec",
            "progress_percentage": 80.0,
            "updated_at": datetime.now().isoformat()
        })

        logger.info("API specification generated", session_id=state["session_id"])
        return state

    except Exception as e:
        logger.error("API spec generation failed", error=str(e))
        state["api_specification"] = "# API Specification generation failed\n# Error: " + str(e)
        return state


async def generate_db_schema_node(state: TechSpecState) -> TechSpecState:
    """Generate database schema with DDL statements."""
    logger.info("Generating database schema", session_id=state["session_id"])

    try:
        llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.3)

        # Determine database type from decisions
        db_tech = "PostgreSQL"  # Default
        for decision in state.get("user_decisions", []):
            if decision.get("category", "").lower() in ["database", "db"]:
                db_tech = decision.get("technology_name", "PostgreSQL")

        prompt = f"""Generate a complete database schema for {db_tech} based on the TRD.

**TRD Content:**
{state['trd_draft'][:5000]}

**Database Technology:** {db_tech}

Generate:
1. Complete DDL statements (CREATE TABLE, indexes, constraints)
2. ERD in Mermaid format
3. Sample data for testing

Include:
- Primary keys, foreign keys
- Appropriate indexes
- Constraints (unique, not null, check)
- Comments explaining relationships
"""

        response = await llm.generate(
            messages=[Message(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=6144
        )

        state.update({
            "database_schema": response.content,
            "current_stage": "generate_db_schema",
            "progress_percentage": 85.0,
            "updated_at": datetime.now().isoformat()
        })

        logger.info("Database schema generated", session_id=state["session_id"])
        return state

    except Exception as e:
        logger.error("DB schema generation failed", error=str(e))
        state["database_schema"] = "-- Schema generation failed\n-- Error: " + str(e)
        return state


async def generate_architecture_node(state: TechSpecState) -> TechSpecState:
    """Generate architecture diagram in Mermaid format."""
    logger.info("Generating architecture diagram", session_id=state["session_id"])

    try:
        llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.3)

        prompt = f"""Generate a system architecture diagram in Mermaid format.

**TRD:**
{state['trd_draft'][:5000]}

**Tech Stack:**
{_format_tech_decisions(state['user_decisions'])}

Create a Mermaid flowchart showing:
- Client applications
- API layer
- Backend services
- Databases
- External services (if any)
- Caching layer (if any)
- File storage (if any)

Use proper Mermaid syntax for flowchart.
"""

        response = await llm.generate(
            messages=[Message(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=2048
        )

        state.update({
            "architecture_diagram": response.content,
            "current_stage": "generate_architecture",
            "progress_percentage": 90.0,
            "updated_at": datetime.now().isoformat()
        })

        logger.info("Architecture diagram generated", session_id=state["session_id"])
        return state

    except Exception as e:
        logger.error("Architecture generation failed", error=str(e))
        state["architecture_diagram"] = "```mermaid\n# Diagram generation failed\n```"
        return state


async def generate_tech_stack_doc_node(state: TechSpecState) -> TechSpecState:
    """Generate technology stack documentation."""
    logger.info("Generating tech stack documentation", session_id=state["session_id"])

    try:
        doc = "# Technology Stack\n\n"

        # Add each technology decision
        for decision in state.get("user_decisions", []):
            doc += f"## {decision['category'].title()}\n\n"
            doc += f"**Selected:** {decision['technology_name']}\n\n"
            if decision.get("reasoning"):
                doc += f"**Reasoning:** {decision['reasoning']}\n\n"
            doc += "---\n\n"

        state.update({
            "tech_stack_document": doc,
            "current_stage": "generate_tech_stack_doc",
            "progress_percentage": 95.0,
            "updated_at": datetime.now().isoformat()
        })

        logger.info("Tech stack documentation generated", session_id=state["session_id"])
        return state

    except Exception as e:
        logger.error("Tech stack doc generation failed", error=str(e))
        state["tech_stack_document"] = "# Technology Stack\n\nGeneration failed."
        return state


# ============= Helper Functions =============

async def _multi_agent_trd_review(trd_content: str, prd_content: str, tech_decisions: list) -> Dict:
    """
    Multi-agent TRD review system with specialized agents for different domains.

    Agents:
    - Architecture Agent: Reviews system architecture and component design
    - Security Agent: Reviews security requirements and OWASP mitigations
    - Performance Agent: Reviews performance, scalability, and caching
    - API Agent: Reviews API specification completeness and design
    - Database Agent: Reviews database schema and optimization

    Args:
        trd_content: The generated TRD content
        prd_content: Original PRD for context
        tech_decisions: User technology decisions

    Returns:
        Dict with aggregated review results from all agents
    """
    llm = LLMClient(model=ModelType.CLAUDE_SONNET, temperature=0.3)

    # Define specialized review agents
    agents = {
        "architecture": {
            "name": "Architecture Agent",
            "focus": "System Architecture section",
            "criteria": """
            - Is the architecture clearly described (3-tier, microservices, etc.)?
            - Are all components and their responsibilities defined?
            - Is data flow between components explained?
            - Are integration points with third-party services documented?
            - Are scalability and fault tolerance addressed?
            """
        },
        "security": {
            "name": "Security Agent",
            "focus": "Security Requirements section",
            "criteria": """
            - Are authentication and authorization mechanisms specified?
            - Is password hashing algorithm mentioned (bcrypt, Argon2)?
            - Is data encryption (at rest and in transit) covered?
            - Are OWASP Top 10 mitigations addressed?
            - Is secrets management strategy defined?
            - Are API security measures (CORS, rate limiting, input validation) documented?
            """
        },
        "performance": {
            "name": "Performance Agent",
            "focus": "Performance Requirements section",
            "criteria": """
            - Are response time targets specified (P50, P95, P99)?
            - Is throughput requirement defined (requests/second)?
            - Is caching strategy detailed (what, TTL, invalidation)?
            - Are database query optimization approaches mentioned?
            - Is horizontal/vertical scaling strategy explained?
            """
        },
        "api": {
            "name": "API Agent",
            "focus": "API Specification section",
            "criteria": """
            - Are at least 5 key endpoints documented?
            - Does each endpoint have request/response examples?
            - Are error responses defined with codes and formats?
            - Is rate limiting strategy specified?
            - Is authentication method clearly described?
            - Is pagination approach documented (if applicable)?
            """
        },
        "database": {
            "name": "Database Agent",
            "focus": "Database Schema section",
            "criteria": """
            - Are all key tables defined with columns and types?
            - Are foreign key relationships documented?
            - Is indexing strategy specified (which fields, why)?
            - Is data migration approach explained?
            - Are constraints (unique, not null, check) mentioned?
            """
        }
    }

    # Collect reviews from all agents
    agent_reviews = {}

    for agent_id, agent_config in agents.items():
        review_prompt = f"""You are the **{agent_config['name']}**, a specialized reviewer for technical requirements documents.

**Your Focus**: {agent_config['focus']}

**Review Criteria:**
{agent_config['criteria']}

**TRD Section to Review:**
{trd_content[:15000]}  # Provide full context

**Original PRD Context:**
{prd_content[:1000]}

**Selected Technologies:**
{_format_tech_decisions(tech_decisions)}

**Task**: Review the {agent_config['focus']} and provide a detailed assessment.

Respond with JSON:
{{
    "score": <0-100>,
    "strengths": ["strength 1", "strength 2", ...],
    "weaknesses": ["weakness 1", "weakness 2", ...],
    "critical_issues": ["issue 1", "issue 2", ...],
    "recommendations": ["recommendation 1", "recommendation 2", ...],
    "missing_elements": ["element 1", "element 2", ...],
    "overall_assessment": "<1-2 sentence summary>"
}}

Be thorough and specific. Focus on actionable feedback."""

        try:
            review = await llm.generate_json(
                messages=[Message(role="user", content=review_prompt)],
                system=f"You are a senior {agent_config['name'].lower()} expert reviewing technical specifications.",
                temperature=0.3,
                max_tokens=2048
            )

            agent_reviews[agent_id] = {
                "agent_name": agent_config['name'],
                "focus_area": agent_config['focus'],
                **review
            }

            logger.info(
                f"{agent_config['name']} review complete",
                agent=agent_id,
                score=review.get("score", 0)
            )

        except Exception as e:
            logger.error(
                f"{agent_config['name']} review failed",
                agent=agent_id,
                error=str(e)
            )
            # Provide fallback review on error
            agent_reviews[agent_id] = {
                "agent_name": agent_config['name'],
                "focus_area": agent_config['focus'],
                "score": 50,
                "strengths": [],
                "weaknesses": ["Review failed due to error"],
                "critical_issues": [],
                "recommendations": ["Manual review recommended"],
                "missing_elements": [],
                "overall_assessment": f"Review failed: {str(e)}"
            }

    # Aggregate results
    avg_score = sum(r.get("score", 0) for r in agent_reviews.values()) / len(agent_reviews)

    all_critical_issues = []
    all_recommendations = []
    for agent_id, review in agent_reviews.items():
        # Prefix critical issues with agent name
        all_critical_issues.extend([
            f"[{review['agent_name']}] {issue}"
            for issue in review.get("critical_issues", [])
        ])
        # Prefix recommendations with agent name
        all_recommendations.extend([
            f"[{review['agent_name']}] {rec}"
            for rec in review.get("recommendations", [])[:2]  # Top 2 per agent
        ])

    return {
        "multi_agent_score": avg_score,
        "agent_reviews": agent_reviews,
        "critical_issues": all_critical_issues,
        "recommendations": all_recommendations,
        "review_summary": {
            agent_id: {
                "score": review.get("score", 0),
                "assessment": review.get("overall_assessment", "")
            }
            for agent_id, review in agent_reviews.items()
        }
    }


def _validate_trd_structure(trd_content: str) -> Tuple[bool, List[Dict], int]:
    """
    Validate TRD structure programmatically before LLM validation.

    Checks for:
    - Required section headings
    - Minimum content length per section
    - Presence of code blocks and examples
    - Proper Markdown formatting

    Args:
        trd_content: The generated TRD markdown content

    Returns:
        Tuple of (is_valid, issues, structure_score)
        - is_valid: True if all critical sections present
        - issues: List of validation issues found
        - structure_score: 0-100 score based on structure completeness
    """
    issues = []
    structure_score = 100

    # Define required sections with minimum content expectations
    required_sections = {
        "Project Overview": {"min_length": 200, "weight": 5},
        "Technology Stack": {"min_length": 500, "weight": 20},
        "System Architecture": {"min_length": 300, "weight": 15},
        "API Specification": {"min_length": 600, "weight": 20},
        "Database Schema": {"min_length": 400, "weight": 15},
        "Security Requirements": {"min_length": 300, "weight": 10},
        "Performance Requirements": {"min_length": 200, "weight": 5},
        "Deployment Strategy": {"min_length": 200, "weight": 5},
        "Testing Strategy": {"min_length": 200, "weight": 5},
        "Development Guidelines": {"min_length": 150, "weight": 5}
    }

    # Check for each required section
    missing_sections = []
    short_sections = []

    for section_name, requirements in required_sections.items():
        # Look for section heading (## Section Name or # Section Name)
        pattern = rf"#{{1,3}}\s+\d*\.?\s*{re.escape(section_name)}"
        match = re.search(pattern, trd_content, re.IGNORECASE)

        if not match:
            missing_sections.append(section_name)
            structure_score -= requirements["weight"]
            issues.append({
                "section": section_name,
                "issue": f"Section heading not found",
                "severity": "high"
            })
        else:
            # Extract section content (from this heading to next # heading)
            start_pos = match.end()
            next_heading = re.search(r"\n#+ ", trd_content[start_pos:])
            end_pos = start_pos + next_heading.start() if next_heading else len(trd_content)
            section_content = trd_content[start_pos:end_pos].strip()

            # Check minimum length
            if len(section_content) < requirements["min_length"]:
                short_sections.append(section_name)
                structure_score -= requirements["weight"] // 2
                issues.append({
                    "section": section_name,
                    "issue": f"Section too short ({len(section_content)} chars, expected {requirements['min_length']}+)",
                    "severity": "medium"
                })

    # Check for code blocks (should have at least 5 for examples)
    code_blocks = re.findall(r"```[\s\S]*?```", trd_content)
    if len(code_blocks) < 5:
        structure_score -= 10
        issues.append({
            "section": "Overall",
            "issue": f"Insufficient code examples ({len(code_blocks)} found, expected 5+)",
            "severity": "medium"
        })

    # Check for API endpoint patterns (should have multiple endpoints documented)
    api_endpoints = re.findall(r"(?:GET|POST|PUT|DELETE|PATCH)\s+/\w+", trd_content)
    if len(api_endpoints) < 3:
        structure_score -= 10
        issues.append({
            "section": "API Specification",
            "issue": f"Too few API endpoints documented ({len(api_endpoints)} found, expected 3+)",
            "severity": "medium"
        })

    # Check for version numbers (technologies should have versions)
    version_patterns = re.findall(r"\d+\.\d+\.\d+", trd_content)
    if len(version_patterns) < 5:
        structure_score -= 5
        issues.append({
            "section": "Technology Stack",
            "issue": f"Insufficient version specifications ({len(version_patterns)} found, expected 5+)",
            "severity": "low"
        })

    # Check for rationale/justification keywords
    rationale_keywords = ["rationale", "reason", "why", "because", "chosen", "selected"]
    rationale_count = sum(1 for keyword in rationale_keywords if keyword in trd_content.lower())
    if rationale_count < 3:
        structure_score -= 5
        issues.append({
            "section": "Overall",
            "issue": "Insufficient technology rationales/justifications",
            "severity": "low"
        })

    # Ensure score doesn't go negative
    structure_score = max(0, structure_score)

    # Determine if valid (all critical sections present, score >= 60)
    is_valid = len(missing_sections) == 0 and structure_score >= 60

    # Log validation results
    logger.info(
        "TRD structure validation complete",
        structure_score=structure_score,
        is_valid=is_valid,
        missing_sections=missing_sections,
        short_sections=short_sections,
        code_blocks=len(code_blocks),
        api_endpoints=len(api_endpoints)
    )

    return is_valid, issues, structure_score


def _build_trd_prompt(state: TechSpecState) -> str:
    """Build comprehensive TRD generation prompt with few-shot examples."""
    return f"""Generate a comprehensive Technical Requirements Document (TRD) for this project.

**Original PRD:**
{state['prd_content'][:3000]}

**Design Documents:**
{_format_design_docs_summary(state['design_docs'])}

**Selected Technology Stack:**
{_format_tech_decisions(state['user_decisions'])}

**Inferred API Endpoints:**
{str(state.get('inferred_apis', []))[:1500]}

**Code Analysis Summary:**
{str(state.get('code_analysis_summary', {}))[:1000]}

---

**IMPORTANT**: Follow the format and detail level shown in these examples:

## EXAMPLE 1: Technology Stack Section (High Quality)

```markdown
## 2. Technology Stack

### 2.1 Frontend
- **Framework**: Next.js 14.2.3 (App Router)
  - **Rationale**: Server-side rendering for SEO, built-in API routes, optimal performance
  - **Key Features**: React Server Components, automatic code splitting, image optimization
- **UI Library**: shadcn/ui + Radix UI primitives
  - **Rationale**: Accessible components, customizable with Tailwind CSS
- **State Management**: Zustand 4.5.2
  - **Rationale**: Lightweight, minimal boilerplate, TypeScript-first
- **Form Validation**: React Hook Form + Zod
  - **Rationale**: Type-safe validation, excellent DX, automatic error handling

### 2.2 Backend
- **Framework**: NestJS 10.3.2
  - **Rationale**: Enterprise-grade architecture, built-in DI, modular structure
  - **Key Modules**: @nestjs/jwt, @nestjs/passport, @nestjs/swagger
- **API Documentation**: Swagger/OpenAPI 3.0
  - **Auto-generated**: From NestJS decorators
- **Validation**: class-validator + class-transformer
  - **Rationale**: DTO validation at controller level

### 2.3 Database
- **Primary Database**: PostgreSQL 14.11
  - **Rationale**: ACID compliance, JSON support, robust querying
- **ORM**: Prisma 5.12.1
  - **Rationale**: Type-safe queries, automatic migrations, excellent DX
- **Caching**: Redis 7.2
  - **Use Cases**: Session storage, rate limiting, real-time data caching

### 2.4 Authentication
- **Library**: NextAuth.js 4.24.7
  - **Providers**: Email/password, Google OAuth 2.0, GitHub
  - **Session Strategy**: JWT with refresh tokens
  - **Security**: HTTP-only cookies, CSRF protection
```

## EXAMPLE 2: API Specification Section (High Quality)

```markdown
## 4. API Specification

### 4.1 Authentication

**Base URL**: `https://api.example.com/v1`

**Authentication Method**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <token>`
- **Token Expiry**: 15 minutes (access token), 7 days (refresh token)
- **Refresh Endpoint**: `POST /auth/refresh`

### 4.2 Endpoints

#### POST /auth/login
**Description**: Authenticate user and return JWT tokens

**Request Body**:
```json
{{
  "email": "user@example.com",
  "password": "securePassword123"
}}
```

**Response (200 OK)**:
```json
{{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
  "user": {{
    "id": "uuid-here",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "user"
  }},
  "expiresIn": 900
}}
```

**Error Responses**:
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Rate limit exceeded (max 5 attempts per 15 min)

#### GET /projects/:projectId
**Description**: Retrieve project details by ID

**Parameters**:
- `projectId` (path, required): UUID of the project

**Response (200 OK)**:
```json
{{
  "id": "uuid-here",
  "name": "My Project",
  "description": "Project description",
  "status": "active",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T12:00:00Z",
  "owner": {{
    "id": "user-uuid",
    "name": "John Doe"
  }},
  "members": [...]
}}
```

**Error Responses**:
- `404 Not Found`: Project does not exist
- `403 Forbidden`: User lacks permission to view project

### 4.3 Rate Limiting
- **Global Limit**: 100 requests per minute per IP
- **Authenticated Limit**: 1000 requests per minute per user
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### 4.4 Error Format
All errors follow this structure:
```json
{{
  "error": {{
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {{
      "field": "Specific field error if applicable"
    }},
    "timestamp": "2025-01-15T10:00:00Z"
  }}
}}
```
```

---

**NOW GENERATE THE COMPLETE TRD** with these 10 sections, matching the detail level shown above:

# 1. Project Overview
- Project name and description
- Version and date
- Stakeholders
- Document purpose and scope

# 2. Technology Stack
Follow EXAMPLE 1 format - be specific with versions, rationales, and key features for:
- Frontend technologies (framework, UI, state, forms, etc.)
- Backend technologies (framework, API docs, validation)
- Database and ORM (include caching strategy)
- Authentication/Authorization (library, providers, session strategy)
- File storage (if applicable)
- External services (payment, email, analytics, etc.)
- CI/CD and deployment tools

# 3. System Architecture
- High-level architecture overview (3-tier, microservices, etc.)
- Component breakdown with responsibilities
- Data flow diagrams (describe in text or use Mermaid)
- Integration points between components
- Third-party service integrations

# 4. API Specification
Follow EXAMPLE 2 format - include:
- Base URL and versioning strategy
- Authentication methods with token details
- **At least 5-10 key endpoints** with full request/response examples
- Error handling with standard error format
- Rate limiting strategy with specific limits
- Pagination approach (if applicable)

# 5. Database Schema
- Entity relationship overview
- **Detailed table definitions** (columns, types, constraints)
- Foreign key relationships
- Indexing strategy (which fields, why)
- Data migration strategy (tools, approach)

# 6. Security Requirements
- Authentication and authorization mechanisms
- Password policies and storage (hashing algorithm)
- Data encryption (at rest, in transit)
- API security (CORS, rate limiting, input validation)
- OWASP Top 10 mitigations (specific to this project)
- Secrets management approach

# 7. Performance Requirements
- Response time targets (P50, P95, P99)
- Throughput requirements (requests/second)
- Scalability considerations (horizontal/vertical)
- Caching strategy (what to cache, TTL, invalidation)
- Database query optimization approach

# 8. Deployment Strategy
- Environment setup (dev, staging, production configs)
- CI/CD pipeline (tools, stages, triggers)
- Container strategy (Docker, Kubernetes if applicable)
- Monitoring and logging (tools, metrics, alerts)
- Backup and disaster recovery (frequency, retention, RTO/RPO)

# 9. Testing Strategy
- Unit testing (framework, coverage target, approach)
- Integration testing (tools, critical flows)
- E2E testing (framework, key user journeys)
- Performance testing (tools, load scenarios)
- Security testing (SAST, DAST, penetration testing)

# 10. Development Guidelines
- Code style and standards (linting, formatting tools)
- Git workflow (branching strategy, commit conventions)
- Code review process (checklist, approval requirements)
- Documentation requirements (API docs, inline comments, README)
- Definition of Done checklist

**CRITICAL REQUIREMENTS**:
1. **Be Specific**: Include exact versions, command examples, configuration snippets
2. **Be Actionable**: Developers should be able to start implementation immediately
3. **Be Comprehensive**: Cover all aspects from development to deployment
4. **Use Consistent Formatting**: Follow Markdown best practices
5. **Include Code Examples**: API request/response formats, configuration samples
6. **Provide Rationales**: Explain WHY each technology/approach was chosen
7. **Match the Input**: Use the selected technologies and inferred APIs provided above

Generate the TRD now in Markdown format.
"""


def _format_design_docs_summary(design_docs: Dict[str, str]) -> str:
    """Format design docs summary for prompts."""
    summary = []
    for doc_type, content in design_docs.items():
        if content:
            summary.append(f"- {doc_type}: {len(content)} characters")
    return "\n".join(summary) if summary else "No design documents"


def _format_tech_decisions(decisions: list) -> str:
    """Format user technology decisions for prompts."""
    if not decisions:
        return "No technology decisions made yet"

    formatted = []
    for decision in decisions:
        formatted.append(f"- {decision['category']}: {decision['technology_name']}")

    return "\n".join(formatted)
