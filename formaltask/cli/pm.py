"""FormalTask v5 CLI - Project management commands.

Entry point for all pm-* commands using modern Python CLI pattern.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from formaltask.cli.commands import discover_plugins


class AgentFriendlyParser(argparse.ArgumentParser):
    """ArgumentParser with concise error messages for token efficiency.

    Standard argparse outputs 1000+ character errors listing all commands.
    This parser produces ~100 character errors suitable for LLM agents.
    """

    def error(self, message: str) -> None:
        """Print concise error message and exit.

        Args:
            message: The error message from argparse.
        """
        # Extract invalid command from argparse message
        # Format: "invalid choice: 'xyz' (choose from ...)"
        match = re.search(r"invalid choice: '([^']+)'", message)
        if match:
            invalid_cmd = match.group(1)
            # Get valid commands for fuzzy matching
            valid_commands = list(discover_plugins().keys())
            matches = difflib.get_close_matches(invalid_cmd, valid_commands, n=1, cutoff=0.5)
            if matches:
                error_msg = f"Error: Unknown command '{invalid_cmd}'. Did you mean: {matches[0]}? Run: ft --help"
            else:
                error_msg = f"Error: Unknown command '{invalid_cmd}'. Run: ft --help"
        else:
            error_msg = f"Error: {message}. Run: ft --help"
        sys.stderr.write(error_msg + "\n")
        sys.exit(2)


from formaltask.db.path import get_db_path

# Parent parser with global flags (add_help=False to avoid -h conflict)
parent_parser = argparse.ArgumentParser(add_help=False)

# Output format flags (mutually exclusive)
output_group = parent_parser.add_mutually_exclusive_group()
output_group.add_argument("--json", action="store_true", help="Output in JSON format")
output_group.add_argument("--stream", action="store_true", help="Stream output progressively")

# Execution mode flags (mutually exclusive)
mode_group = parent_parser.add_mutually_exclusive_group()
mode_group.add_argument("--preflight", action="store_true", help="Validate without executing")
mode_group.add_argument("--dry-run", action="store_true", help="Show what would be done")


def main() -> int:
    """Main entry point for pm CLI."""
    parser = AgentFriendlyParser(
        prog="ft",
        description="FormalTask v5 project management commands",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
JSON Output Examples:
  ft --json task list my-epic
    {"success": true, "data": {"tasks": [...], "total": 5, "epic_name": "my-epic"}}

  ft --json epic list
    {"success": true, "data": {"epics": [...], "total": 10}}

Global Flags (before subcommand):
  --json       Output in JSON format (machine-readable)
  --stream     Stream output progressively
  --preflight  Validate without executing
  --dry-run    Show what would be done
""",
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Discover and register plugin-based commands
    plugins = discover_plugins()
    for command_name, plugin_module in plugins.items():
        plugin_subparser = subparsers.add_parser(
            command_name,
            help=plugin_module.COMMAND_HELP,
        )
        plugin_module.setup_parser(plugin_subparser)

    args = parser.parse_args()

    # Resolve db_path if not explicitly provided
    # Skip for setup — it creates the database and handles its own path
    if args.command != "setup" and hasattr(args, "db_path") and args.db_path is None:
        try:
            args.db_path = str(get_db_path())
        except FileNotFoundError as e:
            print(f"Error: Database not found - {e}", file=sys.stderr)
            print("  Run 'ft setup' to initialize, or ensure you're in the correct project directory.", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Security error: {e}", file=sys.stderr)
            return 1

    # Dispatch to plugin-based commands
    if args.command in plugins:
        return plugins[args.command].execute(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
