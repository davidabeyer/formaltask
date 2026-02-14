"""Conversation-only transcript extractor for handoff generation.

Extracts user prompts and assistant text from JSONL transcripts,
removing all tool_use entries (unlike slim_transcript.py which keeps them).
"""

import json
from pathlib import Path


def truncate_thinking(text: str, head: int = 500, tail: int = 200) -> str:
    """Truncate thinking blocks to head + tail if too long.

    Preserves decision-relevant content at start and end.
    """
    text = text.strip()
    if len(text) <= head + tail + 50:  # Small buffer to avoid awkward truncation
        return text
    return f"{text[:head]}\n[...{len(text) - head - tail} chars truncated...]\n{text[-tail:]}"


def handoff_transcript(transcript_path: Path, start_line: int = 0) -> str:
    """Extract conversation-only transcript from start_line onward.

    Keeps:
    - User prompts (full text, no truncation)
    - Assistant text responses (full text, no truncation)
    - Thinking blocks (truncated: first 500 + last 200 chars if long)

    Removes:
    - ALL tool_use entries
    - ALL tool_result entries

    Args:
        transcript_path: Path to JSONL transcript file.
        start_line: 0-indexed line number to start extraction from.

    Returns:
        Formatted conversation transcript as string.
    """
    output_lines = []

    with open(transcript_path) as f:
        for line_num, line in enumerate(f):
            if line_num < start_line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")

            # Skip tool results entirely
            if entry_type == "tool_result":
                continue

            if entry_type == "user":
                msg = entry.get("message", {})
                content = msg.get("content", msg.get("message", ""))
                if isinstance(content, str) and content.strip():
                    output_lines.append(f"USER: {content.strip()}\n")

            elif entry_type == "assistant":
                msg = entry.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    text_parts = []
                    thinking_parts = []

                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get("type")

                        # Skip tool_use entirely
                        if item_type == "tool_use":
                            continue

                        if item_type == "text":
                            text = item.get("text", "").strip()
                            if text:
                                text_parts.append(text)

                        elif item_type == "thinking":
                            thinking = item.get("thinking", "").strip()
                            if thinking:
                                thinking_parts.append(truncate_thinking(thinking))

                    if text_parts:
                        output_lines.append(f"CLAUDE: {' '.join(text_parts)}\n")
                    if thinking_parts:
                        output_lines.append(f"THINKING: {' '.join(thinking_parts)}\n")

    return "".join(output_lines)
