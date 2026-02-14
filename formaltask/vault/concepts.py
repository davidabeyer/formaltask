"""Vault concept management — cache, weekly folders, index pages, migration.

Pure I/O + grep. No LLM calls.
"""

import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def get_week_folder(vault_dir: Path, d: date) -> Path:
    """Return sessions/{year}-W{week:02d}/, creating if needed."""
    iso = d.isocalendar()
    folder = vault_dir / "sessions" / f"{iso[0]}-W{iso[1]:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def parse_frontmatter(text: str) -> dict:
    """Extract full YAML frontmatter as dict. Returns {} on parse failure."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    if not isinstance(fm, dict):
        return {}
    return fm


def parse_frontmatter_concepts(text: str) -> list[str]:
    """Extract concepts list from YAML frontmatter. Returns [] on parse failure."""
    fm = parse_frontmatter(text)
    if not fm:
        return []
    concepts = fm.get("concepts", [])
    if isinstance(concepts, str):
        return [concepts]
    if isinstance(concepts, list):
        return [str(c) for c in concepts]
    return []


def get_concept_list(vault_dir: Path) -> list[str]:
    """Read .concepts.txt cache. Fallback: grep all session frontmatter."""
    cache = vault_dir / ".concepts.txt"
    if cache.exists():
        lines = [ln.strip() for ln in cache.read_text().splitlines() if ln.strip()]
        return sorted(set(lines))

    # Fallback: scan session files
    sessions_dir = vault_dir / "sessions"
    if not sessions_dir.is_dir():
        return []
    concepts = set()
    for f in sessions_dir.rglob("*.md"):
        concepts.update(parse_frontmatter_concepts(f.read_text()))
    return sorted(concepts)


def update_concept_cache(vault_dir: Path, new_concepts: list[str]) -> None:
    """Merge new_concepts into .concepts.txt, dedup, sort, atomic write."""
    cache = vault_dir / ".concepts.txt"
    existing = set()
    if cache.exists():
        existing = {ln.strip() for ln in cache.read_text().splitlines() if ln.strip()}
    existing.update(c for c in new_concepts if c)
    if existing:
        # Atomic: write to tmp in same dir, then rename (safe against races)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text("\n".join(sorted(existing)) + "\n")
        os.replace(tmp, cache)


def materialize_concepts(vault_dir: Path) -> None:
    """For each concept in cache, generate pages/{concept}.md listing all sessions."""
    cache = vault_dir / ".concepts.txt"
    if not cache.exists():
        return
    concepts = [ln.strip() for ln in cache.read_text().splitlines() if ln.strip()]
    if not concepts:
        return

    pages_dir = vault_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Build concept → [(title, relative_path, date)] map
    concept_refs: dict[str, list[tuple[str, str, str]]] = {c: [] for c in concepts}

    sessions_dir = vault_dir / "sessions"
    if not sessions_dir.is_dir():
        return

    for f in sorted(sessions_dir.rglob("*.md")):
        text = f.read_text()
        file_concepts = parse_frontmatter_concepts(text)
        # Extract title
        title = "Untitled"
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        # Extract date from frontmatter or filename
        fm_date = ""
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1))
                if isinstance(fm, dict):
                    fm_date = str(fm.get("date", ""))
            except yaml.YAMLError:
                pass
        if not fm_date:
            # Try filename: YYYY-MM-DD-...
            name_match = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
            fm_date = name_match.group(1) if name_match else ""

        rel_path = f"../sessions/{f.parent.name}/{f.name}"
        for c in file_concepts:
            if c in concept_refs:
                concept_refs[c].append((title, rel_path, fm_date))

    for concept, refs in concept_refs.items():
        if not refs:
            continue
        lines = [f"# {concept.replace('-', ' ').title()}\n"]
        for title, rel_path, d in refs:
            if d:
                lines.append(f"- [{title}]({rel_path}) — {d}")
            else:
                lines.append(f"- [{title}]({rel_path})")
        (pages_dir / f"{concept}.md").write_text("\n".join(lines) + "\n")


def generate_session_index(vault_dir: Path) -> None:
    """Generate INDEX.md listing all sessions newest-first with title and summary."""
    sessions_dir = vault_dir / "sessions"
    if not sessions_dir.is_dir():
        return

    entries: list[tuple[str, str, str, str]] = []  # (date, title, summary, rel_path)

    for f in sessions_dir.rglob("*.md"):
        text = f.read_text()
        fm = parse_frontmatter(text)
        fm_date = str(fm.get("date", ""))
        summary = str(fm.get("summary", ""))

        if not fm_date:
            name_match = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
            fm_date = name_match.group(1) if name_match else ""

        title = "Untitled"
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        rel_path = f"sessions/{f.parent.name}/{f.name}"
        entries.append((fm_date, title, summary, rel_path))

    if not entries:
        return

    # Sort newest first, keep only last 2 weeks
    entries.sort(key=lambda e: e[0], reverse=True)
    cutoff = (date.today() - timedelta(weeks=2)).isoformat()
    entries = [e for e in entries if e[0] >= cutoff]

    if not entries:
        return

    lines = ["# Session Index\n"]
    for fm_date, title, summary, rel_path in entries:
        lines.append(f"### [{title}]({rel_path})")
        lines.append(f"*{fm_date}*")
        if summary:
            lines.append(f"\n{summary}")
        lines.append("")

    (vault_dir / "INDEX.md").write_text("\n".join(lines) + "\n")


def migrate_vault(vault_dir: Path) -> None:
    """Move root session files to sessions/{week}/, add minimal frontmatter.

    One-time migration for existing vault files. Safe to re-run (skips
    files already in sessions/).
    """
    if not vault_dir.is_dir():
        logger.info("migrate_vault: vault dir %s not found", vault_dir)
        return

    # Find session files at vault root (YYYY-MM-DD-*.md pattern)
    for f in sorted(vault_dir.glob("*.md")):
        name_match = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md", f.name)
        if not name_match:
            continue

        file_date = date(
            int(name_match.group(1)),
            int(name_match.group(2)),
            int(name_match.group(3)),
        )
        week_folder = get_week_folder(vault_dir, file_date)

        text = f.read_text()
        # Add frontmatter if missing
        if not text.startswith("---\n"):
            # Extract session_id from filename (last segment before .md)
            slug = name_match.group(4)
            iso = file_date.isocalendar()
            frontmatter = (
                f"---\n"
                f"session: {slug}\n"
                f"date: {file_date.isoformat()}\n"
                f"week: {iso[0]}-W{iso[1]:02d}\n"
                f"concepts: []\n"
                f"---\n"
            )
            text = frontmatter + text

        dest = week_folder / f.name
        dest.write_text(text)
        f.unlink()
        logger.info("migrate_vault: %s → %s", f.name, dest)

    # Clean up legacy config files
    for legacy in [".schema.yaml", ".tag-aliases.yaml"]:
        p = vault_dir / legacy
        if p.exists():
            p.unlink()
            logger.info("migrate_vault: deleted %s", legacy)
