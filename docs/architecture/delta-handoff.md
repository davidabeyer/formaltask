# Delta Handoff

Context preservation across conversation compaction. Captures decisions, failed approaches, and gotchas before compaction destroys them, then re-injects on session resume.

## The problem

When Claude Code compacts a conversation, the compaction summary flattens nuance: decision rationale, failed approaches, and user corrections get lost. The compaction summary is injected directly into conversation context — hooks cannot access it. Delta handoff works around this by snapshotting the transcript *before* compaction and extracting key context via LLM.

## Data flow

```
PreCompact hooks                     SessionStart hooks
─────────────────                    ──────────────────

transcript_snapshot.py               delta_handoff.py
  │                                    │
  ├── find last compaction line        ├── detect .session/transcript_snapshot.json
  ├── extract conversation since       ├── truncate to 30k chars (keep recent)
  └── write .session/transcript_       ├── GPT 5.2 → DeltaHandoff (5 list[str])
      snapshot.json                    ├── write handoff file
                                       ├── write breadcrumb
handoff_generator.py                   └── inject via hookSpecificOutput
  │
  ├── detect .session/name             run_session_file() (phases/__init__.py)
  ├── full transcript → GPT 5.2          │
  ├── → HandoffResponse (6 fields)       ├── .session/name → thread name
  └── write_handoff() + breadcrumb       ├── find_prev_handoff() from index
                                          └── inject previous handoff markdown
carry_forward.py
  │
  └── write compacting-session.json    run_adopt_compacted_breadcrumbs()
      (old session_id for re-tagging)    │
                                          └── re-tag orphaned skill breadcrumbs
```

## Module map

| File | Role |
| --- | --- |
| `hooks/pre_compact/transcript_snapshot.py` | Snapshot transcript before compaction (pure I/O, no LLM) |
| `hooks/pre_compact/handoff_generator.py` | Full handoff via GPT 5.2 → `HandoffResponse` (6 fields) |
| `hooks/pre_compact/handoff_writer.py` | Thread-first directory output, sequence numbers, thread index |
| `hooks/pre_compact/handoff_transcript.py` | Conversation-only transcript extractor (strips tool_use/tool_result) |
| `hooks/pre_compact/carry_forward.py` | Persist old session_id for breadcrumb re-tagging |
| `hooks/session_start/delta_handoff.py` | Post-compaction: snapshot → GPT 5.2 → `DeltaHandoff` → inject |
| `hooks/session_start/phases/__init__.py` | `run_session_file()` — load previous handoff for worktree sessions |

## DeltaHandoff schema

`DeltaHandoff` (Pydantic model in `delta_handoff.py`):

| Field | Type | Content |
| --- | --- | --- |
| `decision_rationale` | `list[str]` | "Chose X because Y" — the WHY that compaction flattens |
| `failed_approaches` | `list[str]` | "Tried X, failed because Y" — skipped entirely by compaction |
| `user_corrections` | `list[str]` | "User said X" — preferences that got flattened |
| `technical_gotchas` | `list[str]` | Specific errors, versions, edge cases discovered |
| `implementation_proposals` | `list[str]` | Code snippets, file paths, function signatures proposed |

Empty lists are valid — means nothing was lost in that category.

## HandoffResponse schema

`HandoffResponse` (Pydantic model in `handoff_generator.py`):

| Field | Type | Content |
| --- | --- | --- |
| `summary` | `str` (max 500) | Brief summary of what was accomplished |
| `decisions` | `list[str]` | Key decisions with rationale |
| `completed` | `list[str]` | Tasks/items completed |
| `pending` | `list[str]` | Tasks/items still pending |
| `context` | `str` | Additional context for continuity |
| `files_touched` | `list[str]` | Files modified or read |

## Activation

Both systems activate via `.session/name` file in the working directory (worktree-only):

1. `cc thread-name` creates `.session/name` with the thread name
2. PreCompact hooks check for this file — skip if absent
3. SessionStart `run_session_file()` checks for this file to load previous handoff

Non-worktree sessions (main repo) never generate or consume handoffs.

## Thread index

Handoff storage follows a thread-first directory structure:

```
~/.claude/handoffs/
├── thread-index.json              # {thread_name: [relative_paths]}
└── my-thread/
    ├── 01--2026-01-15--initial-setup.md
    ├── 02--2026-01-15--auth-flow-decisions.md
    └── 03--2026-01-16--STUB.md    # Failed API call, manual recovery needed
```

Filenames: `{sequence:02d}--{date}--{summary_slug}.md`. Sequence numbers auto-increment per thread.

Breadcrumb file: `~/.claude/projects/{project_id}/handoff-thread.txt` — contains the active thread name so SessionStart can find the previous handoff without knowing the thread name.

## Files

| Path | Purpose |
| --- | --- |
| `hooks/pre_compact/transcript_snapshot.py` | Pre-compaction transcript snapshot |
| `hooks/pre_compact/handoff_generator.py` | Full handoff generation (GPT 5.2) |
| `hooks/pre_compact/handoff_writer.py` | File output, thread indexing, breadcrumbs |
| `hooks/pre_compact/handoff_transcript.py` | Conversation-only transcript extraction |
| `hooks/pre_compact/carry_forward.py` | Session ID carry-forward for breadcrumb re-tagging |
| `hooks/session_start/delta_handoff.py` | Delta generation + injection (post-compaction) |
| `hooks/session_start/phases/__init__.py` | `run_session_file()` — previous handoff loading |
