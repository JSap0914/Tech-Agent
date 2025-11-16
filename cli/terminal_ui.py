"""
Terminal UI components using Rich for beautiful CLI output.
"""

from typing import Dict, List, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
import structlog

logger = structlog.get_logger(__name__)

console = Console()


def print_header():
    """Print Tech Spec Agent CLI header."""
    header_text = """
================================================================
           TECH SPEC AGENT - CLI Interface
================================================================
  Generate Technical Requirements Documents from PRD & Design
================================================================
    """
    console.print(header_text, style="bold cyan")
    console.print()


def print_section(title: str, style: str = "bold yellow"):
    """
    Print a section header.

    Args:
        title: Section title
        style: Rich style string
    """
    console.print(f"\n{'='*70}", style=style)
    console.print(f"  {title}", style=style)
    console.print(f"{'='*70}\n", style=style)


def print_success(message: str):
    """Print success message."""
    console.print(f"[OK] {message}", style="bold green")


def print_error(message: str):
    """Print error message."""
    console.print(f"[ERROR] {message}", style="bold red")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[WARNING] {message}", style="bold yellow")


def print_info(message: str):
    """Print info message."""
    console.print(f"[INFO] {message}", style="cyan")


def print_agent_message(message: str, role: str = "agent"):
    """
    Print agent or user message.

    Args:
        message: Message content
        role: "agent" or "user"
    """
    if role == "agent":
        console.print(f"\n[bold cyan]Agent:[/bold cyan] {message}\n")
    else:
        console.print(f"\n[bold green]User:[/bold green] {message}\n")


def display_completeness_score(score: float, missing: List[str], ambiguous: List[str]):
    """
    Display PRD completeness analysis.

    Args:
        score: Completeness score (0-100)
        missing: List of missing elements
        ambiguous: List of ambiguous elements
    """
    print_section("PRD Completeness Analysis")

    # Score panel
    score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
    score_text = f"[{score_color}]{score}/100[/{score_color}]"

    console.print(f"Completeness Score: {score_text}", style="bold")
    console.print()

    # Missing elements
    if missing:
        console.print("[bold red]Missing Elements:[/bold red]")
        for item in missing:
            console.print(f"  • {item}", style="red")
        console.print()

    # Ambiguous elements
    if ambiguous:
        console.print("[bold yellow]Ambiguous Elements:[/bold yellow]")
        for item in ambiguous:
            console.print(f"  • {item}", style="yellow")
        console.print()


def display_technology_options(
    category: str,
    options: List[Dict],
    current_gap: int,
    total_gaps: int
):
    """
    Display technology options in a formatted table.

    Args:
        category: Technology category (e.g., "authentication")
        options: List of 3 technology options with pros/cons/metrics
        current_gap: Current gap number (1-indexed)
        total_gaps: Total number of gaps
    """
    print_section(f"Technology Research: {category.upper()} ({current_gap}/{total_gaps})")

    table = Table(
        title=f"Select Technology for {category}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("#", style="cyan", width=3)
    table.add_column("Technology", style="bold")
    table.add_column("Metrics", style="dim")
    table.add_column("Pros", style="green")
    table.add_column("Cons", style="red")

    for idx, option in enumerate(options[:3], 1):
        name = option.get("technology_name", "Unknown")
        metrics = option.get("metrics", {})
        pros = option.get("pros", [])
        cons = option.get("cons", [])

        # Format metrics
        metrics_str = "\n".join([
            f"Stars: {metrics.get('github_stars', 'N/A')}",
            f"Downloads: {metrics.get('npm_downloads', 'N/A')}",
            f"Updated: {metrics.get('last_update', 'N/A')}"
        ])

        # Format pros/cons
        pros_str = "\n".join([f"+ {p[:40]}" for p in pros[:3]])
        cons_str = "\n".join([f"- {c[:40]}" for c in cons[:3]])

        # Highlight recommended option
        if option.get("recommended", False):
            name = f"[*] {name}"

        table.add_row(
            str(idx),
            name,
            metrics_str,
            pros_str,
            cons_str
        )

    console.print(table)
    console.print()


def display_conflict_warning(conflicts: List[Dict]):
    """
    Display technology conflicts.

    Args:
        conflicts: List of conflict dictionaries
    """
    print_warning("Potential Conflicts Detected")

    for conflict in conflicts:
        severity = conflict.get("severity", "warning")
        message = conflict.get("message", "")
        details = conflict.get("details", "")

        panel_style = "red" if severity == "critical" else "yellow"

        panel_content = f"[bold]{message}[/bold]\n\n{details}"

        console.print(Panel(
            panel_content,
            title=f"[!] {severity.upper()}",
            border_style=panel_style,
            box=box.ROUNDED
        ))
        console.print()


def display_progress(
    current_stage: str,
    progress_percentage: float,
    message: Optional[str] = None
):
    """
    Display workflow progress.

    Args:
        current_stage: Current workflow stage name
        progress_percentage: Progress (0-100)
        message: Optional status message
    """
    phase = get_phase_from_progress(progress_percentage)

    progress_bar = "█" * int(progress_percentage / 2) + "░" * (50 - int(progress_percentage / 2))

    console.print(
        f"\n[bold cyan]{phase}[/bold cyan] | "
        f"[bold white]{current_stage}[/bold white] | "
        f"[{progress_bar}] {progress_percentage:.1f}%"
    )

    if message:
        console.print(f"  {message}", style="dim")


def get_phase_from_progress(progress: float) -> str:
    """
    Get phase name from progress percentage.

    Args:
        progress: Progress percentage (0-100)

    Returns:
        Phase name
    """
    if progress < 25:
        return "Phase 1: Input & Analysis"
    elif progress < 50:
        return "Phase 2: Technology Research"
    elif progress < 65:
        return "Phase 3: Code Analysis"
    elif progress < 100:
        return "Phase 4: Document Generation"
    else:
        return "Completed"


def display_generated_documents(documents: Dict[str, str], output_dir: str):
    """
    Display summary of generated documents.

    Args:
        documents: Dictionary mapping document type to content
        output_dir: Output directory path
    """
    print_section("Generated Documents")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold green")
    table.add_column("Document Type", style="cyan")
    table.add_column("Size", style="dim")
    table.add_column("Status", style="green")

    for doc_type, content in documents.items():
        size = f"{len(content):,} chars"
        table.add_row(
            doc_type.replace("_", " ").title(),
            size,
            "[OK] Generated"
        )

    console.print(table)
    console.print()
    print_success(f"All documents saved to: {output_dir}")


def display_session_info(session_id: str, project_id: str):
    """
    Display session information.

    Args:
        session_id: Session UUID
        project_id: Project UUID
    """
    print_info(f"Session ID: {session_id}")
    print_info(f"Project ID: {project_id}")
    console.print()


def display_error_panel(error: Exception, traceback_str: Optional[str] = None):
    """
    Display error in a panel.

    Args:
        error: Exception instance
        traceback_str: Optional traceback string
    """
    error_content = f"[bold red]{type(error).__name__}:[/bold red] {str(error)}"

    if traceback_str:
        error_content += f"\n\n[dim]{traceback_str}[/dim]"

    console.print(Panel(
        error_content,
        title="[ERROR]",
        border_style="red",
        box=box.HEAVY
    ))


def create_progress_bar() -> Progress:
    """
    Create a Rich progress bar for long-running operations.

    Returns:
        Progress instance
    """
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    )


def print_conversation_history(history: List[Dict]):
    """
    Print formatted conversation history.

    Args:
        history: List of conversation message dictionaries
    """
    print_section("Conversation History")

    for msg in history:
        role = msg.get("role", "unknown")
        message = msg.get("message", "")
        timestamp = msg.get("timestamp", "")

        if role == "agent":
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[bold cyan]Agent:[/bold cyan] {message}\n")
        elif role == "user":
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[bold green]User:[/bold green] {message}\n")
        else:
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[yellow]{message}[/yellow]\n")


def display_markdown(content: str):
    """
    Display markdown content.

    Args:
        content: Markdown string
    """
    md = Markdown(content)
    console.print(md)
