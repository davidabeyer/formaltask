"""ft work — manage parallel workers (spawn, list, inbox, watch, dashboard, resume, restart, blocked, report)."""

COMMAND_NAME = "work"
COMMAND_HELP = "Manage parallel workers (spawn, list, inbox, watch, dashboard, resume, restart, blocked, report)"

_VERBS = {
    "spawn": ("spawn", "Spawn workers for tasks"),
    "list": ("spawnable", "List spawnable tasks"),
    "inbox": ("inbox", "Show blocked workers awaiting human input"),
    "watch": ("watch", "Monitor workers, optionally spawn new ready tasks"),
    "dashboard": ("dashboard", "TUI dashboard for monitoring parallel workers"),
    "resume": ("resume", "Resume workers from existing Claude sessions"),
    "restart": ("restart_dead", "Restart orphaned workers"),
    "blocked": ("blocked", "Mark worker as blocked with a question"),
    "report": ("report", "Report a blocker issue (creates blocker task)"),
}


def _load_verb(module_name):
    import importlib

    return importlib.import_module(f"formaltask.cli.commands.{module_name}")


def setup_parser(subparser):
    verbs = subparser.add_subparsers(dest="verb", help="Worker commands")
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
        print("Error: No verb specified. Run: ft work --help")
        return 1
    module_name = _VERBS[verb][0]
    try:
        mod = _load_verb(module_name)
    except (ImportError, SyntaxError) as e:
        print(f"Error: Failed to load 'work {verb}': {e}")
        return 1
    return mod.execute(args)
