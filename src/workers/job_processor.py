"""
Job processor for asynchronous workflow execution and resumption.

Handles:
- User decision processing
- LangGraph workflow resumption after user input
- Checkpointer state updates
- Background workflow execution
"""

from typing import Dict, Optional
import asyncio
import structlog

from src.langgraph.workflow import create_tech_spec_workflow
from src.langgraph.state import TechSpecState
from src.langgraph.checkpointer import create_checkpointer
from src.websocket.connection_manager import manager
from src.workers.decision_parser import UserDecision

logger = structlog.get_logger()


class JobProcessor:
    """
    Processes background jobs for Tech Spec Agent workflows.

    Singleton instance responsible for:
    - Resuming workflows after user decisions
    - Managing workflow state via checkpointer
    - Coordinating between WebSocket and LangGraph
    """

    def __init__(self):
        """Initialize job processor."""
        self.active_workflows: Dict[str, asyncio.Task] = {}
        logger.info("job_processor_initialized")

    async def process_user_decision(
        self,
        session_id: str,
        decision: UserDecision
    ) -> None:
        """
        Process user decision and resume LangGraph workflow.

        This is the critical function that unblocks the workflow after user
        provides technology selection via WebSocket.

        Args:
            session_id: Tech Spec session UUID
            decision: Parsed user decision object

        Flow:
            1. Load current workflow state from checkpointer
            2. Update state with user decision
            3. Resume workflow from wait_user_decision node
            4. Workflow continues to next nodes (validate_decision → etc.)

        Example:
            >>> decision = UserDecision(
            ...     category="authentication",
            ...     selected_technology="NextAuth.js",
            ...     reasoning="Best for Next.js"
            ... )
            >>> await job_processor.process_user_decision(session_id, decision)
            # Workflow resumes and continues execution
        """
        logger.info(
            "processing_user_decision",
            session_id=session_id,
            category=decision.category,
            technology=decision.selected_technology
        )

        try:
            # Step 1: Get workflow checkpointer
            checkpointer = create_checkpointer()

            # Step 2: Load current workflow state
            config = {"configurable": {"thread_id": session_id}}
            current_state = await checkpointer.aget(config)

            if not current_state:
                logger.error(
                    "workflow_state_not_found",
                    session_id=session_id
                )
                await manager.send_error(
                    session_id,
                    "Workflow state not found. Please restart the session.",
                    error_type="state_error"
                )
                return

            # Step 3: Update state with user decision
            # Add decision to user_decisions list (the field workflow actually checks!)
            state_values = current_state.values

            from datetime import datetime

            # Append to user_decisions list
            if "user_decisions" not in state_values:
                state_values["user_decisions"] = []

            state_values["user_decisions"].append({
                "category": decision.category,
                "technology_name": decision.selected_technology,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
                "timestamp": datetime.now().isoformat()
            })

            # Remove category from pending_decisions
            pending_decisions = state_values.get("pending_decisions", [])
            if decision.category in pending_decisions:
                pending_decisions.remove(decision.category)

            # Unpause workflow to allow continuation
            state_values["paused"] = False

            # Update progress counters
            state_values["completed_decisions"] = len(state_values["user_decisions"])

            # Step 4: Create updated state
            updated_state = TechSpecState(**state_values)
            updated_state["pending_decisions"] = pending_decisions

            # Step 5: Resume workflow execution
            logger.info(
                "resuming_workflow",
                session_id=session_id,
                next_node="validate_decision"
            )

            # Send progress update
            await manager.send_progress_update(
                session_id=session_id,
                progress=float(state_values.get("completion_percentage", 0)) + 5,
                message=f"Processing {decision.selected_technology} selection...",
                stage="validate_decision"
            )

            # Create and run workflow
            workflow = create_tech_spec_workflow()

            # Run workflow from current state (it will continue from next node)
            result = await workflow.ainvoke(
                updated_state,
                config=config
            )

            logger.info(
                "workflow_resumed_successfully",
                session_id=session_id,
                final_stage=result.get("current_stage")
            )

        except Exception as e:
            logger.error(
                "user_decision_processing_failed",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )

            await manager.send_error(
                session_id,
                f"Failed to process decision: {str(e)}",
                error_type="workflow_error",
                recoverable=True
            )

    async def start_workflow(
        self,
        session_id: str,
        initial_state: TechSpecState
    ) -> None:
        """
        Start new workflow execution.

        Args:
            session_id: Tech Spec session UUID
            initial_state: Initial workflow state

        Note:
            This creates a background task that runs the workflow asynchronously
            while WebSocket connection sends progress updates.
        """
        logger.info("starting_workflow", session_id=session_id)

        try:
            # Create workflow
            workflow = create_tech_spec_workflow()

            # Configure with session-specific checkpointer
            config = {"configurable": {"thread_id": session_id}}

            # Create background task for workflow execution
            task = asyncio.create_task(
                self._run_workflow_background(workflow, initial_state, config, session_id)
            )

            # Track active workflow
            self.active_workflows[session_id] = task

            logger.info("workflow_started", session_id=session_id)

        except Exception as e:
            logger.error(
                "workflow_start_failed",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )

            await manager.send_error(
                session_id,
                f"Failed to start workflow: {str(e)}",
                error_type="workflow_error",
                recoverable=False
            )

    async def _run_workflow_background(
        self,
        workflow,
        initial_state: TechSpecState,
        config: Dict,
        session_id: str
    ) -> None:
        """
        Run workflow in background and send progress updates via WebSocket.

        Args:
            workflow: LangGraph workflow instance
            initial_state: Initial state
            config: Workflow configuration with checkpointer
            session_id: Session ID for WebSocket updates
        """
        try:
            # Stream workflow execution
            async for event in workflow.astream(initial_state, config):
                # Send progress updates for each node completion
                for node_name, node_output in event.items():
                    progress = node_output.get("completion_percentage", 0)
                    stage = node_output.get("current_stage", node_name)
                    message = f"Completed: {stage}"

                    await manager.send_progress_update(
                        session_id=session_id,
                        progress=progress,
                        message=message,
                        stage=stage
                    )

                    logger.info(
                        "workflow_progress",
                        session_id=session_id,
                        node=node_name,
                        progress=progress
                    )

            logger.info("workflow_completed", session_id=session_id)

        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )

            await manager.send_error(
                session_id,
                f"Workflow execution failed: {str(e)}",
                error_type="workflow_error",
                recoverable=False
            )

        finally:
            # Clean up active workflow tracking
            if session_id in self.active_workflows:
                del self.active_workflows[session_id]

    async def cancel_workflow(self, session_id: str) -> bool:
        """
        Cancel active workflow for session.

        Args:
            session_id: Session ID

        Returns:
            True if workflow was canceled, False if no active workflow
        """
        if session_id not in self.active_workflows:
            return False

        task = self.active_workflows[session_id]
        task.cancel()

        logger.info("workflow_canceled", session_id=session_id)
        return True


# Global singleton instance
job_processor = JobProcessor()
