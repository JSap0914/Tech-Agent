"""
CLI workflow runner that executes LangGraph workflow with terminal UI.
"""

import asyncio
from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime
from pathlib import Path
import json
import structlog

from src.langgraph.workflow import create_tech_spec_workflow
from src.langgraph.state import create_initial_state, TechSpecState
from src.langgraph.checkpointer import get_checkpoint_config
from src.database.connection import db_manager
from src.langgraph.nodes import research_nodes

from cli.terminal_ui import (
    print_header,
    print_section,
    print_success,
    print_error,
    print_info,
    print_warning,
    print_agent_message,
    display_completeness_score,
    display_progress,
    display_generated_documents,
    display_session_info,
    display_error_panel,
    console
)
from cli.decision_handler import DecisionHandler

logger = structlog.get_logger(__name__)


class CLIWorkflowRunner:
    """
    Runs Tech Spec workflow with CLI interface.

    Replaces WebSocket communication with terminal I/O.
    """

    def __init__(self):
        """Initialize workflow runner."""
        self.decision_handler = DecisionHandler()
        self.workflow = None
        self.current_state: Optional[TechSpecState] = None

    async def run_workflow(
        self,
        prd_content: str,
        design_docs: Dict[str, str],
        ai_studio_code_path: Optional[str],
        output_dir: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Execute complete Tech Spec workflow.

        Args:
            prd_content: PRD content
            design_docs: Design documents dictionary
            ai_studio_code_path: Optional path to Google AI Studio ZIP
            output_dir: Output directory for generated documents
            project_id: Optional project ID (generates UUID if not provided)
            user_id: Optional user ID (generates UUID if not provided)

        Returns:
            True if successful, False otherwise
        """
        print_header()

        # Generate IDs
        session_id = str(uuid4())
        project_id = project_id or str(uuid4())
        user_id = user_id or str(uuid4())
        design_job_id = str(uuid4())  # Not used in CLI, but required for state

        display_session_info(session_id, project_id)

        try:
            # Register CLI decision callback so LangGraph nodes can block for input
            research_nodes.register_user_decision_callback(self._handle_user_decision_callback)

            # Confirm start
            if not self.decision_handler.confirm_start(
                len(prd_content),
                len(design_docs)
            ):
                print_info("Workflow cancelled by user.")
                return False

            # Create initial state
            print_section("Initializing Workflow")
            state = create_initial_state(
                session_id=session_id,
                project_id=project_id,
                user_id=user_id,
                design_job_id=design_job_id
            )

            # Populate state with inputs
            state.update({
                "prd_content": prd_content,
                "design_docs": design_docs,
                "ai_studio_code_path": ai_studio_code_path
            })

            self.current_state = state

            # Initialize database engine (required by some workflow nodes)
            print_info("Initializing database connection...")
            try:
                db_manager.initialize_async_engine()
                print_success("Database engine initialized")
            except Exception as e:
                print_warning(f"Database initialization failed: {str(e)}")
                print_info("Continuing without database (some features may be limited)")

            # Create workflow
            print_info("Creating LangGraph workflow...")
            self.workflow = create_tech_spec_workflow()

            # Get checkpoint config for resumability
            config = get_checkpoint_config(session_id)

            print_success("Workflow initialized successfully")

            # Execute workflow with streaming
            print_section("Executing Workflow")

            async for event in self.workflow.astream(state, config=config):
                # event is a dict with node names as keys
                for node_name, node_output in event.items():
                    # Update current state
                    self.current_state = node_output

                    # Display progress
                    self._display_node_progress(node_name, node_output)

                    # Handle special nodes that require user interaction
                    if await self._handle_interactive_node(node_name, node_output, config):
                        # Node required user input and workflow will pause
                        # This shouldn't happen in streaming mode, but handle it
                        print_info("Workflow paused. Resuming...")

                    # Handle completeness score display
                    if node_name == "analyze_completeness":
                        self._display_completeness(node_output)

                    # Handle clarification questions
                    if node_output.get("current_stage") == "wait_clarification":
                        await self._handle_clarification(node_output, config)

                    # Handle conflicts
                    if node_name == "warn_user":
                        await self._handle_conflicts(node_output, config)

            # Workflow completed
            print_section("Workflow Completed")

            # Save generated documents
            await self._save_documents(self.current_state, output_dir)

            print_success("Tech Spec generation completed successfully!")
            return True

        except KeyboardInterrupt:
            print_error("\nWorkflow interrupted by user.")
            logger.info("workflow_interrupted", session_id=session_id)
            return False

        except Exception as e:
            print_error(f"Workflow failed: {str(e)}")
            display_error_panel(e)
            logger.error(
                "workflow_execution_failed",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            return False
        finally:
            # Ensure callback is cleared so other contexts (e.g., server) remain unaffected
            research_nodes.register_user_decision_callback(None)

    def _display_node_progress(self, node_name: str, node_output: TechSpecState):
        """
        Display progress for node completion.

        Args:
            node_name: Name of completed node
            node_output: Node output state
        """
        stage = node_output.get("current_stage", node_name)
        progress = node_output.get("progress_percentage", 0.0)

        # Get last agent message
        conversation = node_output.get("conversation_history", [])
        last_message = ""

        for msg in reversed(conversation):
            if msg.get("role") == "agent":
                last_message = msg.get("message", "")
                break

        display_progress(stage, progress, last_message)

    def _display_completeness(self, state: TechSpecState):
        """
        Display completeness score.

        Args:
            state: Current workflow state
        """
        score = state.get("completeness_score", 0.0)
        missing = state.get("missing_elements", [])
        ambiguous = state.get("ambiguous_elements", [])

        display_completeness_score(score, missing, ambiguous)

    async def _handle_interactive_node(
        self,
        node_name: str,
        node_output: TechSpecState,
        config: Dict
    ) -> bool:
        """
        Handle nodes that require user interaction.

        Args:
            node_name: Node name
            node_output: Node output state
            config: Workflow config

        Returns:
            True if node required interaction
        """
        return False

    async def _handle_user_decision_callback(self, state: TechSpecState):
        """
        Callback invoked directly from wait_user_decision node during CLI runs.
        Collects the user's choice and mutates state before the workflow proceeds.
        """
        category = state.get("current_research_category")
        options = state.get("technology_options", {}).get(category, []) if category else []

        if not category or not options:
            logger.warning(
                "wait_user_decision_without_options",
                category=category,
                has_options=bool(options)
            )
            return

        total_gaps = len(state.get("identified_gaps", []))
        decisions_made = len(state.get("user_decisions", []))
        current_gap = decisions_made + 1

        decision = self.decision_handler.get_technology_decision(
            category,
            options,
            current_gap,
            total_gaps
        )

        state["user_decisions"].append({
            "category": decision["category"],
            "technology_name": decision["selected_technology"],
            "reasoning": decision["reasoning"],
            "confidence": decision.get("confidence", "high"),
            "custom_requirements": decision.get("custom_requirements"),
            "timestamp": datetime.now().isoformat()
        })

        pending_decisions = state.get("pending_decisions", [])
        if category in pending_decisions:
            pending_decisions.remove(category)

        state["pending_decisions"] = pending_decisions
        state["paused"] = False
        state["updated_at"] = datetime.now().isoformat()

        logger.info(
            "user_decision_processed",
            category=category,
            technology=decision["selected_technology"]
        )

    async def _handle_clarification(self, state: TechSpecState, config: Dict):
        """
        Handle clarification questions.

        Args:
            state: Current workflow state
            config: Workflow config
        """
        questions_text = state.get("current_question", "")

        if not questions_text:
            return

        # Parse questions (assuming newline-separated)
        questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

        if not questions:
            return

        # Get user answers
        answers = self.decision_handler.get_clarification_answers(questions)

        # Update state
        state["conversation_history"].append({
            "role": "user",
            "message": "\n".join(f"Q{i+1}: {a}" for i, a in enumerate(answers)),
            "timestamp": datetime.now().isoformat()
        })

        # Clear current question
        state["current_question"] = None

        logger.info("clarification_completed", questions_count=len(questions))

    async def _handle_conflicts(self, state: TechSpecState, config: Dict):
        """
        Handle technology conflicts.

        Args:
            state: Current workflow state
            config: Workflow config
        """
        # Extract conflicts from conversation or state
        # This is a simplified version - actual implementation would parse from state
        conflicts = []

        # Check if user wants to reselect
        reselect = self.decision_handler.handle_conflicts(conflicts)

        if reselect:
            # User wants to reselect - clear last decision
            if state.get("user_decisions"):
                last_decision = state["user_decisions"].pop()
                category = last_decision["category"]

                # Add back to pending decisions
                if category not in state.get("pending_decisions", []):
                    state["pending_decisions"].append(category)

                logger.info("decision_reverted", category=category)

    async def _save_documents(self, state: TechSpecState, output_dir: str):
        """
        Save generated documents to filesystem.

        Args:
            state: Final workflow state
            output_dir: Output directory path
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        documents = {}

        # Save TRD
        if state.get("final_trd"):
            trd_path = output_path / f"trd_{timestamp}.md"
            with open(trd_path, 'w', encoding='utf-8') as f:
                f.write(state["final_trd"])
            documents["final_trd"] = state["final_trd"]
            print_success(f"TRD saved: {trd_path}")

        # Save API specification
        if state.get("api_specification"):
            api_path = output_path / f"api_spec_{timestamp}.yaml"
            with open(api_path, 'w', encoding='utf-8') as f:
                f.write(state["api_specification"])
            documents["api_specification"] = state["api_specification"]
            print_success(f"API Spec saved: {api_path}")

        # Save database schema
        if state.get("database_schema"):
            db_path = output_path / f"db_schema_{timestamp}.sql"
            with open(db_path, 'w', encoding='utf-8') as f:
                f.write(state["database_schema"])
            documents["database_schema"] = state["database_schema"]
            print_success(f"DB Schema saved: {db_path}")

        # Save architecture diagram
        if state.get("architecture_diagram"):
            arch_path = output_path / f"architecture_{timestamp}.mmd"
            with open(arch_path, 'w', encoding='utf-8') as f:
                f.write(state["architecture_diagram"])
            documents["architecture_diagram"] = state["architecture_diagram"]
            print_success(f"Architecture saved: {arch_path}")

        # Save tech stack document
        if state.get("tech_stack_document"):
            tech_path = output_path / f"tech_stack_{timestamp}.md"
            with open(tech_path, 'w', encoding='utf-8') as f:
                f.write(state["tech_stack_document"])
            documents["tech_stack_document"] = state["tech_stack_document"]
            print_success(f"Tech Stack saved: {tech_path}")

        # Save session metadata
        metadata = {
            "session_id": state.get("session_id"),
            "project_id": state.get("project_id"),
            "user_id": state.get("user_id"),
            "completed_at": datetime.now().isoformat(),
            "selected_technologies": state.get("selected_technologies", {}),
            "user_decisions": state.get("user_decisions", []),
            "completeness_score": state.get("completeness_score"),
            "errors": state.get("errors", [])
        }

        metadata_path = output_path / f"session_metadata_{timestamp}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        print_success(f"Metadata saved: {metadata_path}")

        # Display summary
        display_generated_documents(documents, str(output_path))
