#!/usr/bin/env python3
"""OpenRouter client helper module using Instructor library.

Provides a unified LLM client for all hooks, using OpenRouter as the API gateway
to access Gemini 2.5 Pro and other models.

This module replaces gemini_client.py and consolidates all LLM API calls through
OpenRouter for simplified API key management and model flexibility.

Example:
    >>> from formaltask.llm.openrouter import get_openrouter_client
    >>> client, model = get_openrouter_client()
    >>> result = client.chat.completions.create(
    ...     model=model,
    ...     response_model=MySchema,
    ...     messages=[{"role": "user", "content": "Hello"}]
    ... )
"""

import logging
import os

from instructor import Instructor, Mode, from_openai
from openai import OpenAI

logger = logging.getLogger(__name__)

# Module constants
DEFAULT_MODEL = "google/gemini-2.5-pro"
BASE_URL = "https://openrouter.ai/api/v1"


def _load_api_key() -> str:
    """Load OpenRouter API key from environment or ~/.claude.json.

    Checks in order:
    1. OPENROUTER_API_KEY environment variable
    2. ~/.claude.json (MCP config file)

    Returns:
        str: The API key, stripped of whitespace.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not found in any location.
    """
    import json
    from pathlib import Path

    # 1. Check environment variable
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key.strip()

    # 2. Check ~/.claude.json (MCP config)
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            with open(claude_json) as f:
                config = json.load(f)
            key = config.get("OPENROUTER_API_KEY")
            if key:
                return key.strip()
            # Search mcpServers.*.env for OPENROUTER_API_KEY
            for server in config.get("mcpServers", {}).values():
                key = server.get("env", {}).get("OPENROUTER_API_KEY")
                if key:
                    return key.strip()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read ~/.claude.json: {e}")

    raise ValueError(
        "OPENROUTER_API_KEY not found. Set the environment variable or add "
        '"OPENROUTER_API_KEY": "sk-or-..." to ~/.claude.json'  # pragma: allowlist secret
    )


def get_openrouter_client(model: str = DEFAULT_MODEL) -> tuple[Instructor, str]:
    """Get configured Instructor client for OpenRouter.

    Creates an OpenAI-compatible client configured for OpenRouter's API endpoint,
    wrapped with Instructor for structured output support using JSON mode.

    Args:
        model: The model identifier to use. Defaults to google/gemini-2.5-pro.
            Other options include anthropic/claude-3-haiku, etc.

    Returns:
        Tuple of (InstructorClient, model_name) where:
            - InstructorClient: Instructor-wrapped client for structured output
            - model_name: The model string to pass to API calls

    Raises:
        ValueError: If API key cannot be loaded.

    Example:
        >>> client, model = get_openrouter_client()
        >>> result = client.chat.completions.create(
        ...     model=model,
        ...     response_model=MyPydanticModel,
        ...     messages=[{"role": "user", "content": "Generate data"}]
        ... )
    """
    api_key = _load_api_key()

    base_client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/anthropics/claude-code",
            "X-Title": "Claude Code Hooks",
        },
    )

    instructor_client = from_openai(base_client, mode=Mode.JSON)

    return instructor_client, model
