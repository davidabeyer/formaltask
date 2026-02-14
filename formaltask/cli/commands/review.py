"""ft review — manage review findings (store, disposition)."""

COMMAND_NAME = "review"
COMMAND_HELP = "Manage review findings (store, disposition)"

_VERBS = {
    "store": ("review_store", "Store a review packet to the database"),
    "disposition": ("disposition", "Mark review findings as wontfix"),
}


def _load_verb(module_name):
    import importlib

    return importlib.import_module(f"formaltask.cli.commands.{module_name}")


def setup_parser(subparser):
    verbs = subparser.add_subparsers(dest="verb", help="Review commands")
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
        print("Error: No verb specified. Run: ft review --help")
        return 1
    module_name = _VERBS[verb][0]
    try:
        mod = _load_verb(module_name)
    except (ImportError, SyntaxError) as e:
        print(f"Error: Failed to load 'review {verb}': {e}")
        return 1
    return mod.execute(args)
