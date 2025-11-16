"""
Integration with Design Agent - Load PRD and design documents.
Implements data ingestion from Design Agent shared tables.
"""

from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.database.models import DesignJob, DesignOutput, DesignDecision
from src.database.connection import db_manager

logger = structlog.get_logger(__name__)

async def load_design_agent_outputs(design_job_id: str) -> Dict[str, str]:
    """
    Load all design outputs from shared.design_outputs table.

    Args:
        design_job_id: UUID of Design Agent job

    Returns:
        Dictionary with PRD, design docs, AI Studio code path
        {
            "prd": "PRD content...",
            "design_system": "Design system content...",
            "ux_flow": "UX flow content...",
            "screen_specs": "Screen specs content...",
            "ai_studio_code_path": "s3://..."
        }

    Raises:
        ValueError: If required documents are missing
    """
    logger.info("Loading design outputs", design_job_id=design_job_id)

    async with db_manager.get_async_session() as session:
        # Query all outputs for this design job
        query = select(DesignOutput).where(DesignOutput.design_job_id == design_job_id)
        result = await session.execute(query)
        outputs = result.scalars().all()

        if not outputs:
            raise ValueError(f"No design outputs found for job {design_job_id}")

        # Build output dictionary
        output_dict = {}
        for output in outputs:
            if output.doc_type == "ai_studio_code":
                output_dict["ai_studio_code_path"] = output.file_path or ""
            else:
                output_dict[output.doc_type] = output.content or ""

        # Validate required documents exist
        required_docs = ["prd", "design_system", "ux_flow", "screen_specs"]
        missing_docs = [doc for doc in required_docs if doc not in output_dict]

        if missing_docs:
            raise ValueError(f"Missing required design documents: {missing_docs}")

        logger.info(
            "Design outputs loaded successfully",
            design_job_id=design_job_id,
            doc_count=len(output_dict)
        )

        return output_dict


async def validate_design_job_completed(design_job_id: str) -> bool:
    """
    Check if Design Agent job is completed and ready for Tech Spec Agent.

    Args:
        design_job_id: UUID of Design Agent job

    Returns:
        True if job is completed

    Raises:
        ValueError: If job is not completed or not found
    """
    logger.info("Validating design job status", design_job_id=design_job_id)

    async with db_manager.get_async_session() as session:
        # Query design job status
        query = select(DesignJob).where(DesignJob.id == design_job_id)
        result = await session.execute(query)
        design_job = result.scalar_one_or_none()

        if not design_job:
            raise ValueError(f"Design job {design_job_id} not found")

        if design_job.status != "completed":
            raise ValueError(
                f"Design job {design_job_id} is not completed (status: {design_job.status})"
            )

        logger.info("Design job validation passed", design_job_id=design_job_id)
        return True


async def load_design_decisions(design_job_id: str) -> List[Dict]:
    """
    Load design decisions from shared.design_decisions table.

    Args:
        design_job_id: UUID of Design Agent job

    Returns:
        List of design decisions with type, value, and reasoning
    """
    logger.info("Loading design decisions", design_job_id=design_job_id)

    async with db_manager.get_async_session() as session:
        # Query all decisions for this design job
        query = select(DesignDecision).where(
            DesignDecision.design_job_id == design_job_id
        )
        result = await session.execute(query)
        decisions = result.scalars().all()

        decision_list = [
            {
                "type": decision.decision_type,
                "value": decision.decision_value,
                "reasoning": decision.reasoning,
                "created_at": decision.created_at.isoformat() if decision.created_at else None
            }
            for decision in decisions
        ]

        logger.info(
            "Design decisions loaded",
            design_job_id=design_job_id,
            decision_count=len(decision_list)
        )

        return decision_list
