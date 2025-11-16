"""
Main CLI entry point for Tech Spec Agent.
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
import structlog

from cli.file_loader import validate_inputs, FileLoadError
from cli.workflow_runner import CLIWorkflowRunner
from cli.terminal_ui import (
    print_header,
    print_success,
    print_error,
    print_info,
    display_error_panel
)

console = Console()
logger = structlog.get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0", prog_name="Tech Spec Agent CLI")
def cli():
    """
    Tech Spec Agent - CLI Interface

    Generate Technical Requirements Documents from PRD and design documents.
    """
    pass


@cli.command()
@click.option(
    "--prd",
    required=True,
    type=click.Path(exists=True),
    help="Path to PRD file (markdown or text)"
)
@click.option(
    "--design-docs",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to design documents folder"
)
@click.option(
    "--ai-studio",
    type=click.Path(exists=True),
    default=None,
    help="Path to Google AI Studio code ZIP (optional)"
)
@click.option(
    "--output",
    type=click.Path(),
    default="./outputs",
    help="Output directory for generated documents (default: ./outputs)"
)
@click.option(
    "--project-id",
    type=str,
    default=None,
    help="Project ID (optional, generates UUID if not provided)"
)
@click.option(
    "--user-id",
    type=str,
    default=None,
    help="User ID (optional, generates UUID if not provided)"
)
def start(prd, design_docs, ai_studio, output, project_id, user_id):
    """
    Start a new Tech Spec workflow.

    Example:
        python cli/main.py start \\
            --prd ./inputs/prd.md \\
            --design-docs ./inputs/design-docs \\
            --output ./outputs
    """
    try:
        # Load and validate inputs
        print_info("Loading input documents...")

        prd_content, design_docs_dict, ai_studio_path = validate_inputs(
            prd_path=prd,
            design_docs_path=design_docs,
            ai_studio_code_path=ai_studio
        )

        print_success("All input documents loaded successfully")

        # Create workflow runner
        runner = CLIWorkflowRunner()

        # Run workflow
        success = asyncio.run(runner.run_workflow(
            prd_content=prd_content,
            design_docs=design_docs_dict,
            ai_studio_code_path=ai_studio_path,
            output_dir=output,
            project_id=project_id,
            user_id=user_id
        ))

        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except FileLoadError as e:
        print_error(f"File loading failed: {str(e)}")
        sys.exit(1)

    except KeyboardInterrupt:
        print_info("\nWorkflow cancelled by user.")
        sys.exit(130)

    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        display_error_panel(e)
        logger.error("cli_error", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--session-id",
    required=True,
    type=str,
    help="Session ID to resume"
)
def resume(session_id):
    """
    Resume a paused Tech Spec workflow.

    Note: This feature requires database checkpointing to be enabled.

    Example:
        python cli/main.py resume --session-id <uuid>
    """
    print_error("Resume functionality not yet implemented in CLI mode.")
    print_info(
        "To enable resume capability, you need:\n"
        "  1. PostgreSQL database running\n"
        "  2. LangGraph checkpointing enabled\n"
        "  3. Session state persisted to database"
    )
    sys.exit(1)


@cli.command()
def list_sessions():
    """
    List all Tech Spec sessions.

    Note: This feature requires database connection.
    """
    print_error("List sessions functionality not yet implemented in CLI mode.")
    print_info(
        "To enable session listing, you need:\n"
        "  1. PostgreSQL database running\n"
        "  2. Access to tech_spec_sessions table"
    )
    sys.exit(1)


@cli.command()
@click.option(
    "--check-db",
    is_flag=True,
    help="Check database connection"
)
@click.option(
    "--check-apis",
    is_flag=True,
    help="Check API keys (Anthropic, Tavily)"
)
def health(check_db, check_apis):
    """
    Check system health and configuration.

    Example:
        python cli/main.py health --check-apis
    """
    print_header()
    print_info("Running health checks...")
    console.print()

    all_healthy = True

    # Check API keys
    if check_apis:
        import os

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")

        if anthropic_key:
            print_success(f"ANTHROPIC_API_KEY: Set (length: {len(anthropic_key)})")
        else:
            print_error("ANTHROPIC_API_KEY: Not set")
            all_healthy = False

        if tavily_key:
            print_success(f"TAVILY_API_KEY: Set (length: {len(tavily_key)})")
        else:
            print_error("TAVILY_API_KEY: Not set")
            all_healthy = False

    # Check database
    if check_db:
        try:
            from src.database.connection import db_manager
            import asyncio

            async def check_db_async():
                db_manager.initialize_async_engine()
                healthy = await db_manager.check_connection()
                return healthy

            db_healthy = asyncio.run(check_db_async())

            if db_healthy:
                print_success("Database: Connected")
            else:
                print_error("Database: Connection failed")
                all_healthy = False

        except Exception as e:
            print_error(f"Database: Error - {str(e)}")
            all_healthy = False

    # Summary
    console.print()
    if all_healthy:
        print_success("All health checks passed!")
        sys.exit(0)
    else:
        print_error("Some health checks failed. Please review the output above.")
        sys.exit(1)


@cli.command()
def example():
    """
    Show example folder structure for inputs.
    """
    print_header()
    console.print("[bold cyan]Expected Folder Structure:[/bold cyan]\n")

    example_structure = """
    project/
    ├── inputs/
    │   ├── prd.md                    # Product Requirements Document
    │   ├── design-docs/
    │   │   ├── design_system.md      # Design system (required)
    │   │   ├── ux_flow.md            # UX flow (required)
    │   │   ├── screen_specs.md       # Screen specs (required)
    │   │   ├── wireframes.md         # Wireframes (optional)
    │   │   └── component_library.md  # Component library (optional)
    │   └── ai_studio_code.zip        # Google AI Studio code (optional)
    └── outputs/                       # Generated documents (auto-created)
        ├── trd_20250116_143022.md
        ├── api_spec_20250116_143022.yaml
        ├── db_schema_20250116_143022.sql
        ├── architecture_20250116_143022.mmd
        ├── tech_stack_20250116_143022.md
        └── session_metadata_20250116_143022.json
    """

    console.print(example_structure, style="dim")
    console.print()

    console.print("[bold yellow]Run the workflow:[/bold yellow]\n")
    console.print("    python cli/main.py start \\", style="green")
    console.print("        --prd ./inputs/prd.md \\", style="green")
    console.print("        --design-docs ./inputs/design-docs \\", style="green")
    console.print("        --output ./outputs", style="green")
    console.print()


if __name__ == "__main__":
    # Configure logging for CLI
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )

    # Run CLI
    cli()
