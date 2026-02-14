"""Doc-Guard configuration loader.

Single source of truth for documented areas configuration.
"""

from pydantic import BaseModel, field_validator

# Module-level cache to avoid repeated YAML parsing (Task #1525)
_config_cache: "DocGuardConfig | None" = None


class DocumentedArea(BaseModel):
    """A documented area with pattern and target CLAUDE.md."""

    pattern: str
    target: str

    @field_validator("pattern")
    @classmethod
    def pattern_not_empty(cls, v: str) -> str:
        """Validate pattern is not empty."""
        if not v:
            raise ValueError("pattern must not be empty")
        return v

    @field_validator("target")
    @classmethod
    def target_not_empty(cls, v: str) -> str:
        """Validate target is not empty."""
        if not v:
            raise ValueError("target must not be empty")
        return v


class Settings(BaseModel):
    """Settings for doc-guard behavior."""

    modification_threshold: int = 20


class DocGuardConfig(BaseModel):
    """Main configuration model for doc-guard."""

    documented_areas: list[DocumentedArea] = []
    settings: Settings = Settings()

    @classmethod
    def with_defaults(cls) -> "DocGuardConfig":
        """Return config with hardcoded defaults when no .doc-guard.yaml exists.

        Default documented areas:
        - hooks/lib/ → hooks/CLAUDE.md
        - hooks/session_end/ → hooks/CLAUDE.md
        - hooks/session_start/ → hooks/CLAUDE.md
        - hooks/cli/ → hooks/cli/CLAUDE.md
        - hooks/cli/commands/ → hooks/cli/CLAUDE.md
        - .claude/skills/ → .claude/CLAUDE.md
        - .claude/commands/ → .claude/CLAUDE.md
        - .claude/agents/ → .claude/CLAUDE.md

        Returns:
            DocGuardConfig with default areas and modification_threshold=20.
        """
        default_areas = [
            ("hooks/lib/", "hooks/CLAUDE.md"),
            ("hooks/session_end/", "hooks/CLAUDE.md"),
            ("hooks/session_start/", "hooks/CLAUDE.md"),
            ("hooks/cli/", "hooks/cli/CLAUDE.md"),
            ("hooks/cli/commands/", "hooks/cli/CLAUDE.md"),
            (".claude/skills/", ".claude/CLAUDE.md"),
            (".claude/commands/", ".claude/CLAUDE.md"),
            (".claude/agents/", ".claude/CLAUDE.md"),
        ]
        return cls(
            documented_areas=[
                DocumentedArea(pattern=pattern, target=target) for pattern, target in default_areas
            ]
        )


def load_config(force_reload: bool = False) -> DocGuardConfig:
    """Load config from PROJECT_ROOT or return defaults.

    Args:
        force_reload: If True, bypass cache and reload from disk.

    Returns:
        DocGuardConfig with documented areas and settings.
    """
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    import os
    from pathlib import Path

    import yaml

    project_root = os.getenv("PROJECT_ROOT", os.getcwd())
    if not Path(project_root).is_absolute():
        raise ValueError("PROJECT_ROOT must be an absolute path")
    if not Path(project_root).exists():
        raise ValueError("PROJECT_ROOT does not exist")
    config_path = Path(project_root) / ".doc-guard.yaml"

    if not config_path.exists():
        config = DocGuardConfig.with_defaults()
        _config_cache = config
        return config

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            config = DocGuardConfig.with_defaults()
            _config_cache = config
            return config
        config = DocGuardConfig(
            documented_areas=[
                DocumentedArea(pattern=area["pattern"], target=area["target"])
                for area in data.get("documented_areas", [])
            ],
            settings=Settings(
                modification_threshold=data.get("settings", {}).get("modification_threshold", 20)
            ),
        )
        _config_cache = config
        return config
    except (OSError, yaml.YAMLError, KeyError, TypeError) as e:
        import logging

        logging.getLogger(__name__).warning("Failed to load .doc-guard.yaml: %s", e)
        config = DocGuardConfig.with_defaults()
        _config_cache = config
        return config


def get_target_for_file(filepath: str) -> str | None:
    """Get the target CLAUDE.md for a file path."""
    from pathlib import Path

    config = load_config()
    file_path = Path(filepath)
    for area in sorted(config.documented_areas, key=lambda a: len(a.pattern), reverse=True):
        pattern_path = Path(area.pattern)
        try:
            file_path.relative_to(pattern_path)
            return area.target
        except ValueError:
            continue
    return None


def matches_documented_area(filepath: str) -> bool:
    """Check if a file path matches any documented area."""
    return get_target_for_file(filepath) is not None
