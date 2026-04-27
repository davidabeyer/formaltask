"""ft task — manage tasks (add, list, show, update, complete, cancel, defer, create-from-finding)."""

COMMAND_NAME = "task"
COMMAND_HELP = "Manage tasks (add, list, show, update, complete, cancel, defer)"

_VERBS = {
    "add": ("task_add", "Add a new task to an epic"),
    "list": ("task_list", "List tasks for an epic"),
    "show": ("task_show", "Show task details"),
    "update": ("task_update", "Update task fields"),
    "start": ("task_start", "Start a task — open → in_progress"),
    "complete": ("task_complete", "Complete a task with code review"),
    "cancel": ("task_cancel", "Cancel a task"),
    "defer": ("task_defer", "Defer a task with a required reason"),
    "create-from-finding": ("defer", "Create a new task from a review finding"),
}


def _load_verb(module_name):
    import importlib

    return importlib.import_module(f"formaltask.cli.commands.{module_name}")


def setup_parser(subparser):
    verbs = subparser.add_subparsers(dest="verb", help="Task commands")
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
        print("Error: No verb specified. Run: ft task --help")
        return 1
    module_name = _VERBS[verb][0]
    try:
        mod = _load_verb(module_name)
    except (ImportError, SyntaxError) as e:
        print(f"Error: Failed to load 'task {verb}': {e}")
        return 1
    return mod.execute(args)
