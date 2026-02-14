"""PreCompact hook: update running session summary. Fail-open.

On each compaction, either creates a new summary (base case) or
updates the existing one with the new transcript segment.
Writes to sessions/{week}/ with YAML frontmatter.
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from formaltask.vault.concepts import (
    get_concept_list,
    get_week_folder,
    parse_frontmatter_concepts,
    update_concept_cache,
)
from formaltask.vault.summarizer import (
    MIN_TURNS,
    count_user_turns,
    find_summary,
    summarize_base,
    summarize_update,
)
from hooks.pre_compact.handoff_transcript import handoff_transcript
from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

logger = logging.getLogger(__name__)

VAULT_DIR = Path.home() / "Documents" / "knowledge" / "vault"


def vault_distill(ctx: dict) -> None:
    """Update running session summary on compaction."""
    # Guard: skip workers
    if Path(".task/id").exists():
        return

    # Guard: no API key
    if not os.getenv("OPENROUTER_API_KEY"):
        return

    transcript_path_str = ctx.get("transcript_path")
    if not transcript_path_str:
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        return

    session_id = transcript_path.stem

    # Extract segment since last compaction
    start_line = find_last_compaction_line(transcript_path)
    segment = handoff_transcript(transcript_path, start_line=start_line)

    vault_dir = VAULT_DIR
    vault_dir.mkdir(parents=True, exist_ok=True)

    concepts = get_concept_list(vault_dir)
    today = datetime.now(UTC).date()
    week_folder = get_week_folder(vault_dir, today)
    week_str = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
    date_str = today.isoformat()

    summary_file = find_summary(vault_dir, session_id)
    result_text = None

    if summary_file:
        # Update existing summary
        current = summary_file.read_text()
        updated = summarize_update(current, segment, concepts=concepts)
        if updated:
            result_text = updated
            summary_file.write_text(result_text)
    else:
        # New summary — check turn threshold
        total_turns = count_user_turns(transcript_path)
        if total_turns < MIN_TURNS:
            return

        result = summarize_base(
            segment,
            session_id=session_id[:8],
            date_str=date_str,
            week_str=week_str,
            concepts=concepts,
        )
        if result:
            result_text = result
            path = week_folder / f"{date_str}-{session_id[:8]}.md"
            path.write_text(result_text)

    if result_text:
        update_concept_cache(vault_dir, parse_frontmatter_concepts(result_text))


def main() -> None:
    payload = json.load(sys.stdin)
    try:
        vault_distill(payload)
    except Exception as e:
        logger.warning("vault_distill failed (non-blocking): %s", e)


if __name__ == "__main__":
    main()
