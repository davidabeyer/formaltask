#!/usr/bin/env python3
"""
PreToolUse Hook: Grep to warp_grep Soft Enforcement
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import json
import re
import sys


def check(ctx: dict) -> dict | None:
    """Validate Grep pattern and suggest alternatives for natural language queries.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed (valid regex pattern or non-Grep tool),
        dict with decision='block' and reason if pattern is natural language.
    """
    tool_name = ctx.get("tool_name", "")

    # Only validate Grep tool
    if tool_name != "Grep":
        return None

    tool_input = ctx.get("tool_input")
    if not isinstance(tool_input, dict):
        return None

    pattern = tool_input.get("pattern", "")
    if not isinstance(pattern, str):
        return None

    is_natural_language, _ = looks_like_natural_language(pattern)
    if is_natural_language:
        query_type = detect_query_type(pattern)
        if query_type == "flow_tracing":
            return {
                "decision": "block",
                "reason": (
                    "This query looks like a cross-file flow tracing question. "
                    "Use mcp__morph-mcp__warp_grep instead for multi-file flow analysis. "
                    "Grep is best for exact symbol/regex patterns."
                ),
            }
        return {
            "decision": "block",
            "reason": (
                "This query looks like a natural language question suited for semantic search. "
                "Use mcp__auggie-mcp__codebase-retrieval (Augment) for semantic understanding. "
                "Grep is best for exact symbol/regex patterns."
            ),
        }

    return None


# Semantic domain concepts that suggest semantic search (P1 fix)
SEMANTIC_CONCEPTS = (
    r"\b(authentication|authorization|database|api|endpoint|"
    r"handler|controller|service|repository|model|"
    r"validation|error|exception|middleware|"
    r"config|configuration|settings|"
    r"test|testing|mock|fixture|flow)\b"
)


def looks_like_natural_language(pattern: str) -> tuple[bool, str]:
    """Determine if a grep pattern looks like natural language rather than regex.

    Args:
        pattern: The grep pattern string to analyze.

    Returns:
        Tuple of (is_natural_language, reason) where reason explains the classification.
    """
    # Simplified: inside [], only \ ] ^ - need escaping (P2.3 fix)
    regex_metacharacters = r"[.*+?\[\](){}^$|\\]"

    if re.search(regex_metacharacters, pattern):
        return False, "contains regex metacharacters"

    # Question words indicate natural language (P2.2: expanded list)
    question_words = r"\b(where|how|what|why|when|which|find|show|list|get|explain)\b"
    if re.search(question_words, pattern, re.IGNORECASE):
        return True, "contains question word"

    # P1 FIX: Multi-word phrases with domain concepts are semantic queries
    words = pattern.strip().split()
    if len(words) >= 2 and re.search(SEMANTIC_CONCEPTS, pattern, re.IGNORECASE):
        return True, "multi-word semantic concept"

    return False, "looks like valid grep pattern"


def detect_query_type(pattern: str) -> str:
    """Classify natural language query type to suggest the best tool.

    This function is only called for patterns that pass looks_like_natural_language().
    Exact symbol searches (e.g., "class Foo") are filtered out earlier and use Grep.

    Args:
        pattern: The grep pattern string (already verified as natural language).

    Returns:
        "flow_tracing" - Multi-file flow questions (warp_grep)
        "semantic" - General semantic queries (Augment)
    """
    pattern_lower = pattern.lower()

    # Flow tracing indicators
    flow_keywords = [
        r"\b(flow|across|between|chain|calls?|trace)\b",
        r"\b(how does .* (call|invoke|trigger|flow))",
        r"\b(from .* to .*)\b",
    ]
    for kw in flow_keywords:
        if re.search(kw, pattern_lower):
            return "flow_tracing"

    return "semantic"


def main() -> None:
    """Hook entry point."""
    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result:
            print(json.dumps(result))
    except json.JSONDecodeError:
        # Fail open for malformed input
        pass


if __name__ == "__main__":
    main()
