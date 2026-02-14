"""CLI command plugin discovery."""

import importlib
import pkgutil
from types import ModuleType

REQUIRED_EXPORTS = ("COMMAND_NAME", "COMMAND_HELP", "setup_parser", "execute")


def _is_valid_plugin(module: ModuleType) -> bool:
    for name in REQUIRED_EXPORTS:
        attr = getattr(module, name, None)
        if attr is None:
            return False
        if name in ("setup_parser", "execute") and not callable(attr):
            return False
    return True


def _module_names():
    """Yield importable module names from this package."""
    try:
        for _importer, name, _ispkg in pkgutil.iter_modules(__path__):
            yield name
    except OSError:
        import os

        if not __path__:
            return
        for entry in os.listdir(__path__[0]):
            entry_path = os.path.join(__path__[0], entry)
            if entry.endswith(".py") and entry != "__init__.py":
                yield entry[:-3]
            elif os.path.isdir(entry_path) and os.path.exists(
                os.path.join(entry_path, "__init__.py")
            ):
                yield entry


def discover_plugins() -> dict[str, ModuleType]:
    """Discover valid command plugin modules in this package."""
    plugins: dict[str, ModuleType] = {}
    for name in _module_names():
        try:
            # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
            module = importlib.import_module(f"{__name__}.{name}")
        except (ImportError, SyntaxError):
            continue
        if _is_valid_plugin(module):
            plugins[module.COMMAND_NAME] = module
    return plugins
