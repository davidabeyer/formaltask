"""ft init command - Alias for 'ft setup'.

Delegates to setup.execute() so 'ft init' and 'ft setup' behave identically.
"""

from formaltask.cli.commands.setup import (  # noqa: F401 (re-exports for plugin discovery)
    execute,
    setup_parser,
)

COMMAND_NAME = "init"
COMMAND_HELP = "Initialize formaltask (alias for 'ft setup')"
