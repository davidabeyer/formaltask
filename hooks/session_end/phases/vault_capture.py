"""SessionEnd hook: finalize session summary with slug rename + concept index.

On session end, either creates or updates the summary, renames to
slug-based filename, and materializes concept index pages.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from formaltask.vault.concepts import (
    generate_session_index,
    get_concept_list,
    get_week_folder,
    materialize_concepts,
    parse_frontmatter_concepts,
    update_concept_cache,
)
from formaltask.vault.summarizer import (
    MIN_TURNS,
    count_user_turns,
    extract_title,
    find_summary,
    slugify_title,
    summarize_base,
    summarize_update,
)
from hooks.pre_compact.handoff_transcript import handoff_transcript
from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

logger = logging.getLogger(__name__)

VAULT_DIR = Path.home() / "Documents" / "knowledge" / "vault"


def _find_transcript(session_id: str) -> Path | None:
    """Locate transcript JSONL by session_id."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.is_dir():
        return None
    for f in projects_dir.rglob(f"{session_id}.jsonl"):
        return f
    return None


def vault_capture(ctx: dict) -> None:
    """Finalize session summary: create/update, rename to slug, materialize concepts."""
    try:
        # Guard: skip workers
        if Path(".task/id").exists():
            return

        # Guard: no API key
        if not os.getenv("OPENROUTER_API_KEY"):
            return

        session_id = ctx.get("session_id")
        if not session_id:
            return

        transcript_path = _find_transcript(session_id)
        if not transcript_path or not transcript_path.exists():
            return

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
            current = summary_file.read_text()
            updated = summarize_update(current, segment, concepts=concepts)
            if updated:
                result_text = updated
                summary_file.write_text(result_text)
            else:
                result_text = current
        else:
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
                summary_file = week_folder / f"{date_str}-{session_id[:8]}.md"
                summary_file.write_text(result_text)

        if not result_text or not summary_file:
            return

        # Rename to slug-based filename
        title = extract_title(result_text)
        slug = slugify_title(title)
        new_name = f"{date_str}-{slug}-{session_id[:8]}.md"
        new_path = summary_file.parent / new_name
        if new_path != summary_file:
            summary_file.rename(new_path)

        # Update concept cache, materialize index pages, regenerate session index
        update_concept_cache(vault_dir, parse_frontmatter_concepts(result_text))
        materialize_concepts(vault_dir)
        generate_session_index(vault_dir)

    except Exception as e:
        logger.warning("vault_capture failed (non-blocking): %s", e)
