"""Unit tests for Design Agent integration."""

import pytest
from uuid import uuid4

from src.integration.design_agent_loader import (
    load_design_agent_outputs,
    validate_design_job_completed,
    load_design_decisions,
)


@pytest.mark.asyncio
async def test_load_design_agent_outputs_missing_job():
    """Test loading outputs for non-existent job raises ValueError."""
    fake_job_id = str(uuid4())

    with pytest.raises(ValueError, match="No design outputs found"):
        await load_design_agent_outputs(fake_job_id)


@pytest.mark.asyncio
async def test_validate_design_job_completed_not_found():
    """Test validating non-existent job raises ValueError."""
    fake_job_id = str(uuid4())

    with pytest.raises(ValueError, match="not found"):
        await validate_design_job_completed(fake_job_id)


@pytest.mark.asyncio
async def test_load_design_decisions_empty():
    """Test loading decisions for job with no decisions."""
    fake_job_id = str(uuid4())

    # Should return empty list, not raise error
    decisions = await load_design_decisions(fake_job_id)
    assert isinstance(decisions, list)
    assert len(decisions) == 0


# TODO: Add integration tests with actual database data
# These tests require database to be set up with Design Agent tables
