"""SessionStart hook: generate delta handoff from pre-compaction transcript.

Standalone script — separate settings.json entry with 90s timeout.
Detects snapshot marker → extracts key context from transcript → writes delta → injects.
Returns: {"hookSpecificOutput": {"additionalContext": "..."}} to stdout.
Fast-exit (<1ms) when no snapshot marker found.

NOTE: Claude Code's compaction summary is NOT accessible from hooks - it's injected
directly into conversation context without being written to the JSONL transcript.
We work around this by extracting context from the pre-compaction transcript directly.
"""

import json
import os
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pydantic import BaseModel

from formaltask.llm.openrouter import get_openrouter_client
from hooks.pre_compact.handoff_writer import write_handoff, write_thread_breadcrumb

DELTA_MODEL = "openai/gpt-5.2"

# Max transcript size to send to LLM (chars). Truncate from start, keep recent context.
MAX_TRANSCRIPT_SIZE = 30000

SYSTEM_PROMPT = """<role>
WHO: Conversation auditor
ATTITUDE: Extract actionable facts, not vague summaries.
</role>

<purpose>
Extract key context from a pre-compaction transcript that will be lost.
</purpose>

Extract into structured fields:
- decision_rationale: "Chose X because Y" - decisions with reasoning
- failed_approaches: "Tried X, failed because Y" - what didn't work
- user_corrections: Explicit user preferences or corrections
- technical_gotchas: Specific errors, versions, edge cases discovered
- implementation_proposals: Code snippets, file paths, function signatures proposed

CONSTRAINTS:
- Be SPECIFIC, not vague ("auth" ❌, "JWT with RS256 for /api/auth" ✓)
- Include code verbatim if important
- Empty list = nothing found (acceptable)
- Focus on the most recent and relevant context"""


class DeltaHandoff(BaseModel):
    """Each field: list of SPECIFIC facts. Empty list = nothing missed (success)."""

    decision_rationale: list[str]  # "Chose X because Y" - the WHY that was lost
    failed_approaches: list[str]  # "Tried X, failed because Y" - skipped entirely
    user_corrections: list[str]  # "User said X" - preferences that got flattened
    technical_gotchas: list[str]  # Specific errors, versions, edge cases
    implementation_proposals: list[str]  # Code snippets, file paths, function signatures


def _format_delta(delta: DeltaHandoff) -> str:
    """Format DeltaHandoff as markdown for injection."""
    parts = []

    if delta.decision_rationale:
        parts.append("## Decision Rationale (lost in compaction)")
        for d in delta.decision_rationale:
            parts.append(f"- {d}")

    if delta.failed_approaches:
        parts.append("\n## Failed Approaches")
        for a in delta.failed_approaches:
            parts.append(f"- {a}")

    if delta.user_corrections:
        parts.append("\n## User Corrections")
        for c in delta.user_corrections:
            parts.append(f"- {c}")

    if delta.technical_gotchas:
        parts.append("\n## Technical Gotchas")
        for g in delta.technical_gotchas:
            parts.append(f"- {g}")

    if delta.implementation_proposals:
        parts.append("\n## Implementation Proposals (code/details dropped)")
        for p in delta.implementation_proposals:
            parts.append(f"- {p}")

    return "\n".join(parts)


def generate_delta(ctx: dict) -> dict | None:
    """Generate delta handoff from pre-compaction transcript.

    Returns hookSpecificOutput dict, or None if not post-compaction.
    """
    cwd = Path(ctx.get("cwd", os.getcwd()))
    snapshot_path = cwd / ".session" / "transcript_snapshot.json"

    if not snapshot_path.exists():
        return None

    snapshot = json.loads(snapshot_path.read_text())
    thread_name = snapshot["thread_name"]
    transcript = snapshot["transcript"]

    # Truncate transcript if too large (keep the END which has most recent context)
    original_len = len(transcript)
    if len(transcript) > MAX_TRANSCRIPT_SIZE:
        transcript = "...[truncated]...\n\n" + transcript[-MAX_TRANSCRIPT_SIZE:]

    # Write debug log for verification
    debug_path = cwd / ".session" / "delta_debug.json"
    debug_log = {
        "thread_name": thread_name,
        "original_transcript_length": original_len,
        "truncated_length": len(transcript),
        "was_truncated": original_len > MAX_TRANSCRIPT_SIZE,
    }
    debug_path.write_text(json.dumps(debug_log, indent=2))

    # Call LLM (requires OPENROUTER_API_KEY)
    if not os.getenv("OPENROUTER_API_KEY"):
        # Clean up snapshot so it doesn't trigger again
        snapshot_path.unlink()
        return None

    # Build LLM prompt
    user_content = f"## Pre-Compaction Transcript\n\n{transcript}"

    # Call LLM with timeout to prevent indefinite hangs
    client, model = get_openrouter_client(model=DELTA_MODEL)
    delta = client.chat.completions.create(
        model=model,
        response_model=DeltaHandoff,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        extra_body={"reasoning": {"effort": "xhigh"}},
        timeout=60.0,  # 60s max for delta generation
    )

    # Write handoff file
    delta_text = _format_delta(delta)
    content = {
        "summary": delta_text,
        "decisions": delta.decision_rationale,
        "failed_approaches": delta.failed_approaches,
        "user_corrections": delta.user_corrections,
        "technical_gotchas": delta.technical_gotchas,
        "implementation_proposals": delta.implementation_proposals,
    }
    write_handoff(thread_name, content)

    # Write breadcrumb if project_id present
    project_id = ctx.get("project_id")
    if project_id:
        write_thread_breadcrumb(thread_name, project_id)

    # Clean up snapshot (consumed)
    snapshot_path.unlink()

    # Return hook output for injection
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"# Delta Handoff (post-compaction)\n\n{delta_text}",
        }
    }


def main() -> None:
    """Entry point for SessionStart hook."""
    payload = json.load(sys.stdin)
    result = generate_delta(payload)
    if result:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
