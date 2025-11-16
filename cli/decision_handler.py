"""
Interactive user decision handler for technology selection.
"""

from typing import Dict, List, Optional
from datetime import datetime

from rich.prompt import Prompt, Confirm
from rich.console import Console
import structlog

from cli.terminal_ui import (
    display_technology_options,
    display_conflict_warning,
    print_error,
    print_info,
    print_warning,
    console
)

logger = structlog.get_logger(__name__)


class DecisionHandler:
    """Handles user technology selection decisions."""

    def __init__(self):
        """Initialize decision handler."""
        self.console = Console()

    def get_technology_decision(
        self,
        category: str,
        options: List[Dict],
        current_gap: int,
        total_gaps: int
    ) -> Dict:
        """
        Get user's technology selection for a category.

        Args:
            category: Technology category (e.g., "authentication")
            options: List of 3 technology options
            current_gap: Current gap number (1-indexed)
            total_gaps: Total number of gaps

        Returns:
            Decision dictionary with:
                - category: str
                - selected_technology: str
                - reasoning: str
                - confidence: str
        """
        # Display options
        display_technology_options(category, options, current_gap, total_gaps)

        # Get user input
        while True:
            choice = Prompt.ask(
                "\n[bold yellow]Your choice[/bold yellow]",
                choices=["1", "2", "3", "ai", "search"],
                default="ai"
            )

            if choice in ["1", "2", "3"]:
                # Numeric choice
                idx = int(choice) - 1
                selected_option = options[idx]

                # Get optional reasoning (with EOF handling)
                try:
                    reasoning = Prompt.ask(
                        "\n[dim]Reasoning for your choice (optional, press Enter to skip)[/dim]",
                        default=""
                    )
                except (EOFError, KeyboardInterrupt):
                    # Handle EOF or Ctrl+C gracefully - reasoning is optional
                    reasoning = ""
                    logger.info("Reasoning prompt skipped (EOF or interrupt)")


                # Determine confidence
                confidence = "high" if selected_option.get("recommended", False) else "medium"

                decision = {
                    "category": category,
                    "selected_technology": selected_option["technology_name"],
                    "reasoning": reasoning or f"Selected based on evaluation criteria",
                    "confidence": confidence,
                    "custom_requirements": None
                }

                logger.info(
                    "user_decision_made",
                    category=category,
                    technology=decision["selected_technology"]
                )

                return decision

            elif choice == "ai":
                # AI recommendation
                recommended = None
                for option in options:
                    if option.get("recommended", False):
                        recommended = option
                        break

                if not recommended:
                    recommended = options[0]  # Fallback to first option

                print_info(f"AI recommends: {recommended['technology_name']}")

                confirm = Confirm.ask(
                    f"[yellow]Accept AI recommendation ({recommended['technology_name']})?[/yellow]",
                    default=True
                )

                if confirm:
                    decision = {
                        "category": category,
                        "selected_technology": recommended["technology_name"],
                        "reasoning": "Accepted AI recommendation based on comprehensive analysis",
                        "confidence": "high",
                        "custom_requirements": None
                    }

                    logger.info(
                        "ai_recommendation_accepted",
                        category=category,
                        technology=decision["selected_technology"]
                    )

                    return decision
                else:
                    print_info("Please select from the options above.")
                    continue

            elif choice == "search":
                # Custom technology selection when automated research is unavailable
                custom_tech = Prompt.ask("\n[cyan]Enter technology name to evaluate[/cyan]").strip()
                if not custom_tech:
                    print_warning("Please provide a technology name to continue.")
                    continue

                custom_reason = Prompt.ask(
                    "\n[dim]Why is this technology a good fit? (optional)[/dim]",
                    default=""
                )

                decision = {
                    "category": category,
                    "selected_technology": custom_tech,
                    "reasoning": custom_reason or "Manual selection provided during CLI run",
                    "confidence": "medium",
                    "custom_requirements": None
                }

                logger.info(
                    "user_custom_technology_selected",
                    category=category,
                    technology=custom_tech
                )

                return decision

    def handle_conflicts(self, conflicts: List[Dict]) -> bool:
        """
        Handle technology conflicts and get user decision.

        Args:
            conflicts: List of conflict dictionaries

        Returns:
            True if user wants to reselect, False to proceed anyway
        """
        display_conflict_warning(conflicts)

        # Check for critical conflicts
        has_critical = any(c.get("severity") == "critical" for c in conflicts)

        if has_critical:
            print_error("Critical conflicts detected. You must reselect technologies.")
            return True

        # Ask user
        reselect = Confirm.ask(
            "\n[yellow]Do you want to reselect technologies to avoid these conflicts?[/yellow]",
            default=True
        )

        if reselect:
            logger.info("user_chose_reselect")
        else:
            logger.warning("user_chose_proceed_with_conflicts")

        return reselect

    def get_clarification_answers(self, questions: List[str]) -> List[str]:
        """
        Get user answers for clarification questions.

        Args:
            questions: List of clarification questions

        Returns:
            List of user answers
        """
        print_info(f"Please answer {len(questions)} clarification questions:")
        console.print()

        answers = []

        for idx, question in enumerate(questions, 1):
            console.print(f"[bold cyan]Question {idx}/{len(questions)}:[/bold cyan]")
            console.print(f"  {question}")
            console.print()

            answer = Prompt.ask(
                "[yellow]Your answer[/yellow]",
                default=""
            )

            answers.append(answer)
            console.print()

            logger.info(
                "clarification_answered",
                question_num=idx,
                answer_length=len(answer)
            )

        return answers

    def confirm_start(self, prd_size: int, design_docs_count: int) -> bool:
        """
        Confirm before starting workflow.

        Args:
            prd_size: Size of PRD content in characters
            design_docs_count: Number of design documents loaded

        Returns:
            True if user confirms, False otherwise
        """
        console.print()
        print_info(f"PRD Size: {prd_size:,} characters")
        print_info(f"Design Documents: {design_docs_count}")
        console.print()

        confirmed = Confirm.ask(
            "[bold yellow]Start Tech Spec workflow?[/bold yellow]",
            default=True
        )

        return confirmed

    def confirm_save(self, output_dir: str) -> bool:
        """
        Confirm before saving documents.

        Args:
            output_dir: Output directory path

        Returns:
            True if user confirms, False otherwise
        """
        return Confirm.ask(
            f"\n[yellow]Save generated documents to {output_dir}?[/yellow]",
            default=True
        )
