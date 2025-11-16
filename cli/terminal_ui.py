"""
Terminal UI components using Rich for beautiful CLI output.
"""

from typing import Dict, List, Optional
from datetime import datetime
import re
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
import structlog

logger = structlog.get_logger(__name__)

# Create console with legacy Windows support (ASCII only)
console = Console(legacy_windows=True, force_terminal=True)


def strip_emojis(text: str) -> str:
    """Remove emojis for Windows CMD compatibility."""
    # Remove emojis and other non-ASCII characters
    # Comprehensive emoji ranges covering all Unicode emoji blocks
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F700-\U0001F77F"  # alchemical symbols
        u"\U0001F780-\U0001F7FF"  # geometric shapes extended
        u"\U0001F800-\U0001F8FF"  # supplemental arrows-C
        u"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
        u"\U0001FA00-\U0001FA6F"  # chess symbols
        u"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        u"\U00002702-\U000027B0"  # dingbats
        u"\U000024C2-\U0001F251"  # enclosed characters
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        u"\U00002600-\U000026FF"  # miscellaneous symbols
        u"\U00002700-\U000027BF"  # dingbats
        u"\U0001F018-\U0001F270"  # various symbols
        u"\U0001F300-\U0001F5FF"  # miscellaneous symbols and pictographs
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text)


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
    safe_title = strip_emojis(title) if sys.platform == "win32" else title
    console.print(f"\n{'='*70}", style=style)
    console.print(f"  {safe_title}", style=style)
    console.print(f"{'='*70}\n", style=style)


def print_success(message: str):
    """Print success message."""
    safe_message = strip_emojis(message) if sys.platform == "win32" else message
    console.print(f"[OK] {safe_message}", style="bold green")


def print_error(message: str):
    """Print error message."""
    safe_message = strip_emojis(message) if sys.platform == "win32" else message
    console.print(f"[ERROR] {safe_message}", style="bold red")


def print_warning(message: str):
    """Print warning message."""
    safe_message = strip_emojis(message) if sys.platform == "win32" else message
    console.print(f"[WARNING] {safe_message}", style="bold yellow")


def print_info(message: str):
    """Print info message."""
    safe_message = strip_emojis(message) if sys.platform == "win32" else message
    console.print(f"[INFO] {safe_message}", style="cyan")


def print_agent_message(message: str, role: str = "agent"):
    """
    Print agent or user message.

    Args:
        message: Message content
        role: "agent" or "user"
    """
    safe_message = strip_emojis(message) if sys.platform == "win32" else message
    if role == "agent":
        console.print(f"\n[bold cyan]Agent:[/bold cyan] {safe_message}\n")
    else:
        console.print(f"\n[bold green]User:[/bold green] {safe_message}\n")


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
            safe_item = strip_emojis(item) if sys.platform == "win32" else item
            console.print(f"  • {safe_item}", style="red")
        console.print()

    # Ambiguous elements
    if ambiguous:
        console.print("[bold yellow]Ambiguous Elements:[/bold yellow]")
        for item in ambiguous:
            safe_item = strip_emojis(item) if sys.platform == "win32" else item
            console.print(f"  • {safe_item}", style="yellow")
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
    console.print(
        "[dim]Enter 1/2/3, type 'ai' for the recommendation, or type 'search' to manually provide a technology name.[/dim]\n"
    )
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
        
        # Strip emojis on Windows
        safe_message = strip_emojis(message) if sys.platform == "win32" else message
        safe_details = strip_emojis(details) if sys.platform == "win32" else details

        panel_content = f"[bold]{safe_message}[/bold]\n\n{safe_details}"

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

    # Use ASCII-safe characters for Windows compatibility
    filled = int(progress_percentage / 2)
    empty = 50 - filled
    progress_bar = "#" * filled + "-" * empty

    console.print(
        f"\n[bold cyan]{phase}[/bold cyan] | "
        f"[bold white]{current_stage}[/bold white] | "
        f"[{progress_bar}] {progress_percentage:.1f}%"
    )

    if message:
        # Strip emojis for Windows compatibility
        safe_message = strip_emojis(message) if sys.platform == "win32" else message
        console.print(f"  {safe_message}", style="dim")


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
        
        safe_message = strip_emojis(message) if sys.platform == "win32" else message

        if role == "agent":
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[bold cyan]Agent:[/bold cyan] {safe_message}\n")
        elif role == "user":
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[bold green]User:[/bold green] {safe_message}\n")
        else:
            console.print(f"[dim]{timestamp}[/dim]")
            console.print(f"[yellow]{safe_message}[/yellow]\n")


def display_markdown(content: str):
    """
    Display markdown content.

    Args:
        content: Markdown string
    """
    md = Markdown(content)
    console.print(md)
