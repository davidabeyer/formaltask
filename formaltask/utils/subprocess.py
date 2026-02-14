"""Subprocess environment variable utilities (Task #986).

Provides secure environment variable handling for subprocess calls
to prevent leaking sensitive or attacker-controlled environment variables.
"""

import os

# Default whitelist of safe system environment variables
DEFAULT_ENV_WHITELIST = frozenset(
    [
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
    ]
)


def build_subprocess_env(
    additional_vars: dict[str, str] | None = None,
    extra_whitelist: list[str] | None = None,
) -> dict[str, str]:
    """Build a sanitized environment dictionary for subprocess calls.

    Args:
        additional_vars: Extra variables to add to the environment (e.g., API keys).
            These are applied LAST and take precedence over whitelisted env vars.
            Callers are responsible for ensuring values are safe.
        extra_whitelist: Additional variable names to include from os.environ.
            Extends the default whitelist for this call only. Callers are
            responsible for ensuring these variables are safe to expose.

    Returns:
        dict[str, str]: Sanitized environment dictionary containing only whitelisted
        variables and explicitly provided values. Values from additional_vars take
        precedence over environment values.
    """
    # Start with default whitelisted variables from environment
    whitelist = DEFAULT_ENV_WHITELIST
    if extra_whitelist:
        whitelist = whitelist | set(extra_whitelist)
    env = {k: v for k, v in os.environ.items() if k in whitelist}

    # Apply explicit variables LAST - they take precedence over environment values
    if additional_vars:
        env.update(additional_vars)
    return env
