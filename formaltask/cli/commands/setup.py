"""ft setup command - Interactive setup wizard for formaltask.

Guides users through post-install configuration:
1. Initialize database
2. Register required hooks
3. Run doctor for final verification
"""

from pathlib import Path

from formaltask.cli.exit_codes import ExitCode
from formaltask.db.schema import ensure_schema_initialized
from formaltask.hooks.register import (
    SettingsNotFoundError,
    SettingsPermissionError,
    register_required_hooks,
)

# Plugin interface exports
COMMAND_NAME = "setup"
COMMAND_HELP = "Interactive setup wizard for formaltask"


def setup_parser(subparser):
    """Set up argument parser for setup command."""
    subparser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-confirm all prompts (non-interactive mode)",
    )
    subparser.add_argument(
        "--db-path",
        help="Database path (default: .claude/formaltask.db)",
    )


def execute(args) -> int:
    """Execute the setup command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        ExitCode indicating success or failure.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm

    from formaltask.cli.commands import doctor

    # Catppuccin Mocha palette (matches dashboard theme)
    YELLOW = "#f9e2af"  # accent/headers
    GREEN = "#a6e3a1"  # success
    RED = "#f38ba8"  # error
    MUTED = "#6c7086"  # dim/skip

    console = Console()
    auto_confirm = args.yes

    cwd = Path.cwd()
    db_path = Path(args.db_path) if args.db_path else (cwd / ".claude" / "formaltask.db")

    console.print(Panel("formaltask setup wizard", style=f"bold {YELLOW}"))

    # Step 1: Initialize database
    if auto_confirm or Confirm.ask("Initialize/verify database?"):
        ensure_schema_initialized(str(db_path))
        console.print(f"[{GREEN}]✓[/{GREEN}] Database initialized")

    # Step 2: Register required hooks
    console.print(Panel.fit("Hook Registration", style=f"bold {YELLOW}"))
    try:
        results = register_required_hooks()
        for hook_type, status in results:
            if status == "registered":
                console.print(f"[{GREEN}]✓[/{GREEN}] {hook_type} hook registered")
            else:
                console.print(f"[{MUTED}]⊘[/{MUTED}] {hook_type} hook skipped (already exists)")
    except SettingsNotFoundError as e:
        console.print(f"[{RED}]✗[/{RED}] Cannot register hooks: settings.json not found")
        console.print(f"[{MUTED}]  Expected at: {e.path}[/{MUTED}]")
        console.print(f"[{MUTED}]  Run Claude Code at least once to create it.[/{MUTED}]")
        return ExitCode.CONFIG_ERROR.value
    except SettingsPermissionError as e:
        console.print(f"[{RED}]✗[/{RED}] Cannot register hooks: permission denied")
        console.print(f"[{MUTED}]  File: {e.path}[/{MUTED}]")
        console.print(f"[{MUTED}]  Check file permissions and try again.[/{MUTED}]")
        return ExitCode.CONFIG_ERROR.value
    except ValueError as e:
        console.print(f"[{RED}]✗[/{RED}] Cannot register hooks: invalid settings.json")
        console.print(f"[{MUTED}]  {e}[/{MUTED}]")
        return ExitCode.CONFIG_ERROR.value

    # Step 3: Run doctor for verification
    console.print("\n[bold]Verification:[/bold]")
    doctor.execute(args)

    return ExitCode.SUCCESS.value
