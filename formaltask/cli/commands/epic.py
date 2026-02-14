"""ft epic — manage epics (create, list, close, decompose, health, review, update)."""

COMMAND_NAME = "epic"
COMMAND_HELP = "Manage epics (create, list, close, decompose, health, review, update)"

_VERBS = {
    "create": ("epic_create", "Create a new epic"),
    "list": ("epic_list", "List all epics"),
    "close": ("epic_close", "Archive an epic when all tasks are complete"),
    "decompose": ("epic_decompose", "Decompose epic spec directory into tasks"),
    "health": ("epic_health", "Check epic for orphaned dependencies"),
    "review": ("epic_review", "Run comprehensive epic-level code review"),
    "update": ("epic_update", "Update epic attributes"),
}


def _load_verb(module_name):
    import importlib

    return importlib.import_module(f"formaltask.cli.commands.{module_name}")


def setup_parser(subparser):
    verbs = subparser.add_subparsers(dest="verb", help="Epic commands")
    for verb_name, (module_name, help_text) in _VERBS.items():
        try:
            mod = _load_verb(module_name)
        except (ImportError, SyntaxError):
            continue
        verb_parser = verbs.add_parser(verb_name, help=help_text)
        mod.setup_parser(verb_parser)


def execute(args) -> int:
    verb = getattr(args, "verb", None)
    if not verb:
        print("Error: No verb specified. Run: ft epic --help")
        return 1
    module_name = _VERBS[verb][0]
    try:
        mod = _load_verb(module_name)
    except (ImportError, SyntaxError) as e:
        print(f"Error: Failed to load 'epic {verb}': {e}")
        return 1
    return mod.execute(args)
