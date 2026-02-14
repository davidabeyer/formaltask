"""Vault summarizer: incremental session summaries via LLM.

On each compaction, feeds (previous summary + new segment) to LLM,
producing an updated markdown summary with YAML frontmatter.
"""

import json
import logging
import os
import re
from pathlib import Path

import openai
import yaml
from openai import OpenAI
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

SUMMARIZE_MODEL = "google/gemini-2.5-pro"
BASE_URL = "https://openrouter.ai/api/v1"
MIN_SEGMENT_LENGTH = 200
MIN_TURNS = 5

BASE_PROMPT = """\
You are writing working notes for a developer's session journal.

INPUT: A conversation transcript from a Claude Code session.

OUTPUT: A markdown session summary with YAML frontmatter.

FORMAT:
---
session: (use SESSION METADATA value)
date: (use SESSION METADATA value)
week: (use SESSION METADATA value)
concepts: [specific-concept-1, specific-concept-2]
summary: (2-4 sentence summary of the session — what was built, decided, or learned)
---
# {2-5 word title describing the session's main topic}

{2-4 paragraph summary. Each paragraph covers one thread of work.}

## Key Decisions
- {Decision}: {Rationale in one sentence}

## What Broke
- {Thing}: {Root cause + fix in one sentence}
(Omit this section if nothing broke.)

CONCEPTS:
- Create concepts specific to THIS session's actual topics. Be precise.
- BAD: "framework-development", "skill-development" (generic categories)
- GOOD: "ai-defensibility", "binding-density", "vault-summarizer" (specific things)
- Check the EXISTING CONCEPTS list — reuse one ONLY if it's genuinely the same topic.
- Concepts: kebab-case, singular, lowercase. Name the specific THING not a generic category.
- List 2-5 top concepts in frontmatter.

RULES:
- Write as the developer's working notes. First person plural ("we chose", "discovered that").
- Every sentence answers: what was decided? what was built? what broke? what was learned?
- KILL: definitions ("X is a technique that..."), process narration ("ran 5 phases"), \
tool behavior ("spawned 3 auditors"), AI explanations copied from transcript.
- KILL: incident reports that only matter for this specific project. \
KEEP: principles that transfer.
- BAD: "The vault is designed as a personal knowledgebase."
- GOOD: "Redesigned vault prompts to kill encyclopedic output. \
Key fix: negative examples + shipped-artifact threshold."
- The title should be specific enough to distinguish this session from others."""

UPDATE_PROMPT = """\
You are updating a developer's running session summary with new content.

INPUT:
1. CURRENT SUMMARY: The session summary so far (with YAML frontmatter).
2. NEW SEGMENT: A new conversation transcript segment from the same session.

OUTPUT: The complete updated summary. Output ONLY the summary — no preamble, \
no "here is the updated summary", no commentary. Start with --- on line 1.

FORMAT (your output must start exactly like this):
---
session: (preserve from CURRENT SUMMARY)
date: (preserve from CURRENT SUMMARY)
week: (preserve from CURRENT SUMMARY)
concepts: [updated-concept-list]
summary: >-
  2-4 sentence summary of the session's current state.
---
# Title

FRONTMATTER:
Preserve session/date/week from CURRENT SUMMARY. Update concepts and summary.
Do NOT add fields not shown above (no title, role, type, status, tags, links, \
topics, or topics_flat in frontmatter — those are body content or don't exist).

CONCEPTS:
- Update concepts if new topics emerged. Keep existing ones that are still relevant.
- Concepts must be specific to the session's actual topics, not generic categories.
- BAD: "framework-development", "skill-development" — GOOD: "ai-defensibility", "vault-summarizer"

RULES:
- Integrate new content into the existing summary. Don't append blindly \
— restructure if the session's direction changed.
- If a decision from the earlier summary was reversed, update it \
(don't keep both versions).
- If a new thread of work started, add a new paragraph to the narrative.
- Add new Key Decisions and What Broke entries as needed.
- Update concepts if the session's focus shifted.
- Update the title if the session's main topic evolved.
- Keep the summary concise. A 10-compaction session shouldn't be 10x longer \
than a 1-compaction session. Compress, don't accumulate.
- Same voice rules: first person plural, working notes, no definitions, \
no process narration."""


def _get_client() -> tuple[OpenAI, str]:
    """Get raw OpenAI client for OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/anthropics/claude-code",
            "X-Title": "Claude Code Hooks",
        },
    )
    return client, SUMMARIZE_MODEL


class SessionFrontmatter(BaseModel):
    """Schema for vault session summary frontmatter.

    Pydantic enforces structure. Unknown LLM-hallucinated fields (role, type,
    status, tags, links, topics, topics_flat) are silently dropped.
    """

    model_config = {"extra": "ignore"}

    session: str = ""
    date: str = ""
    week: str | int = ""
    concepts: list[str] = []
    summary: str = ""

    @field_validator("concepts", mode="before")
    @classmethod
    def coerce_concepts(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [c.strip() for c in v.split(",")]
        if not isinstance(v, list):
            return []
        return v

    @field_validator("date", "week", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        if v is None:
            return ""
        if hasattr(v, "isoformat"):
            return v.isoformat()  # type: ignore[union-attr]
        return str(v)

    def to_yaml(self) -> str:
        """Dump only non-empty fields to YAML."""
        data = {k: v for k, v in self.model_dump().items() if v}
        # Always include concepts even if empty
        if "concepts" not in data:
            data["concepts"] = []
        return yaml.dump(data, default_flow_style=None, sort_keys=False).rstrip("\n")


# Fields for scoring candidate frontmatter blocks. Includes both valid model
# fields AND common LLM hallucinations (title, topics, etc.) — we want to
# *recognize* a real frontmatter attempt even if it uses wrong field names.
_RECOGNIZABLE_FIELDS = set(SessionFrontmatter.model_fields.keys()) | {
    "title",
    "topics",
    "topics_flat",
    "created",
    "role",
    "type",
    "status",
}
# Minimum recognizable fields to consider a block "real" (not a stub)
_MIN_REAL_FIELDS = 2


def _strip_llm_preamble(text: str) -> str:
    """Strip commentary LLMs add before/around the actual output.

    Handles: markdown code fences, preamble text before ---, wrapper like
    'Here is the updated summary:' etc.
    """
    # Strip markdown code fences (```markdown ... ``` or ```yaml ... ```)
    text = re.sub(r"^```(?:markdown|yaml|md)?\s*\n", "", text.strip())
    text = re.sub(r"\n```\s*$", "", text)

    # If text doesn't start with ---, find the first --- and discard preamble
    if not text.startswith("---"):
        idx = text.find("\n---\n")
        if idx >= 0:
            text = text[idx + 1 :]  # keep the ---

    return text


def _extract_best_frontmatter(text: str) -> tuple[dict, str]:
    """Find the best frontmatter block in text, even if buried in body.

    Returns (frontmatter_dict, body_text). If multiple --- blocks exist,
    picks the one with the most recognized fields.
    """
    blocks = list(re.finditer(r"^---\n(.*?)\n---", text, re.DOTALL | re.MULTILINE))

    best_fm: dict = {}
    best_body = text
    best_score = -1

    for block in blocks:
        try:
            fm = yaml.safe_load(block.group(1))
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue

        score = len(set(fm.keys()) & _RECOGNIZABLE_FIELDS)
        if score > best_score:
            best_score = score
            best_fm = fm
            best_body = text[block.end() :].lstrip("\n")

    return best_fm, best_body


def validate_frontmatter(text: str) -> str:
    """Clean LLM output, extract best frontmatter, validate via Pydantic."""
    text = _strip_llm_preamble(text)

    # Try the normal first-block parse
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    raw: dict | None = None
    body = text

    if match:
        try:
            raw = yaml.safe_load(match.group(1))
            body = text[match.end() :]
        except yaml.YAMLError:
            raw = None

    if not isinstance(raw, dict):
        raw = None

    # If first block is a stub (e.g. just `concepts: []`), search for real frontmatter
    if raw is None or len(set(raw.keys()) & _RECOGNIZABLE_FIELDS) < _MIN_REAL_FIELDS:
        found_fm, found_body = _extract_best_frontmatter(text)
        if len(set(found_fm.keys()) & _RECOGNIZABLE_FIELDS) >= _MIN_REAL_FIELDS:
            raw = found_fm
            body = found_body

    if raw is None:
        return f"---\nconcepts: []\n---\n{text}"

    # Rescue LLM field-name mistakes before Pydantic drops them
    if not raw.get("concepts") and raw.get("topics"):
        raw["concepts"] = raw["topics"]
    if not raw.get("date") and raw.get("created"):
        raw["date"] = raw["created"]

    # Pydantic validates, coerces types, drops unknown fields
    fm = SessionFrontmatter.model_validate(raw)
    return f"---\n{fm.to_yaml()}\n---\n{body}"


def summarize_base(
    segment: str,
    session_id: str = "",
    date_str: str = "",
    week_str: str = "",
    concepts: list[str] | None = None,
) -> str | None:
    """Create initial session summary from transcript segment."""
    if len(segment) < MIN_SEGMENT_LENGTH:
        return None
    try:
        client, model = _get_client()
        concepts_text = ", ".join(concepts) if concepts else "none yet"
        user_content = (
            f"SESSION METADATA:\nsession: {session_id}\ndate: {date_str}\nweek: {week_str}\n\n"
            f"EXISTING CONCEPTS:\n{concepts_text}\n\nTRANSCRIPT:\n{segment}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BASE_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        result = response.choices[0].message.content
        if result:
            result = validate_frontmatter(result)
        return result
    except (
        openai.APIError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
    ) as e:
        logger.warning("summarize_base failed: %s", e)
        return None


def summarize_update(
    current_summary: str,
    new_segment: str,
    concepts: list[str] | None = None,
) -> str | None:
    """Update existing session summary with new transcript segment."""
    if len(new_segment) < MIN_SEGMENT_LENGTH:
        return None
    try:
        client, model = _get_client()
        concepts_text = ", ".join(concepts) if concepts else "none yet"
        user_content = (
            f"EXISTING CONCEPTS:\n{concepts_text}\n\n"
            f"CURRENT SUMMARY:\n{current_summary}\n\n"
            f"NEW SEGMENT:\n{new_segment}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": UPDATE_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        result = response.choices[0].message.content
        if result:
            result = validate_frontmatter(result)
        return result
    except (
        openai.APIError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
    ) as e:
        logger.warning("summarize_update failed: %s", e)
        return None


def extract_title(summary: str) -> str:
    """Extract the # title from a summary."""
    for line in summary.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line
    return "# Untitled Session"


def slugify_title(title: str) -> str:
    """Convert a markdown title to a filename slug."""
    title = re.sub(r"^#+\s*", "", title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:50].rstrip("-") if slug else "misc"


def count_user_turns(transcript_path: Path, start_line: int = 0) -> int:
    """Count user messages in transcript JSONL from start_line onward."""
    count = 0
    with open(transcript_path) as f:
        for i, line in enumerate(f):
            if i < start_line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") == "user":
                    count += 1
            except json.JSONDecodeError:
                continue
    return count


def find_summary(vault_dir: Path, session_id: str) -> Path | None:
    """Search sessions/**/ and vault root for existing summary by session_id prefix."""
    if not vault_dir.is_dir():
        return None
    sid_short = session_id[:8]
    sessions_dir = vault_dir / "sessions"
    if sessions_dir.is_dir():
        for f in sessions_dir.rglob(f"*{sid_short}*.md"):
            return f
    # Fallback: vault root (pre-migration files)
    for f in vault_dir.glob(f"*-{sid_short}*.md"):
        return f
    return None
