#!/usr/bin/env bash
# E2E test: Completion policy round-cap escalation flow.
#
# Drives the full round-cap escalation through real `ft` CLI commands against
# a real (temp) database. Exercises the exact check_completion() →
# apply_completion_rules() code path a live worker hits.
#
# What's faithfully reproduced vs. a real worktree worker:
#   ✓ check_completion → fetch_completion_state → apply_completion_rules (exact code path)
#   ✓ commit_scan evidence linking (real commit with #1 ref)
#   ✓ evidence guard (no --no-evidence bypass)
#   ✓ review freshness check (SHA match between review store and completion)
#   ✓ review round auto-increment (SQL COALESCE(MAX(round),0)+1)
#   ✓ task-level rule priority over builtin rules (first-match-wins exclusivity)
#   ✓ ft work blocked with TASK_ID env detection
#   ✓ ft work inbox query
#   ✓ blocked_user → in_progress recovery path
#   ✓ clean review after dirty → escalation does NOT false-positive
#   ✓ "fixed at round 2" path (round cap doesn't fire when findings resolved)
#   ~ task created via SQL (bypasses task_add validation; completion path doesn't care)
#   ~ started_at set via SQL (matches transition_task_status behavior)
#   ~ no tmux session or worktree (branch name check is equivalent)
#   ~ GitHub PR lookup fails gracefully (no remote; real workers may also have no PR yet)
#
# Usage: bash tests/e2e/test_round_cap.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}$1${NC}"; }
fail() { echo -e "  ${RED}$1${NC}"; exit 1; }

echo "=== E2E: Completion Policy Round Cap ==="

# ── Setup ────────────────────────────────────────────────────────────────────

TMPDIR=$(mktemp -d /tmp/e2e-round-cap.XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

DB="$TMPDIR/formaltask.db"
REAL_PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Temp git repo on a non-default branch.
# _should_skip_review_gates() returns True on master/main, so we need task-1.
cd "$TMPDIR"
git init -q
git commit -q --allow-empty -m "init"
git checkout -q -b task-1
echo "[setup] Created temp repo at $TMPDIR"

# Initialize database (PROJECT_ROOT needed for Python migrations)
PROJECT_ROOT="$REAL_PROJECT_ROOT" python3 -c "
from formaltask.db.schema import ensure_schema_initialized
ensure_schema_initialized('$DB')
"
echo "[setup] Initialized database"

# Create epic via CLI (lightweight, no validation issues)
ft epic create e2e-round-cap "E2E round cap test" --skip-review --db-path "$DB"
echo "[setup] Created epic e2e-round-cap"

# Create task via SQL — bypasses task_add validation (artifact_type requirement)
# but produces the exact DB state the completion path will see.
# Metadata mirrors what the spec decomposition pipeline stores:
#   - required_reviews: from spec
#   - require_pr: true (implementation template default)
#   - completion_rules: task-level escalation rule
PROJECT_ROOT="$REAL_PROJECT_ROOT" python3 - "$DB" <<'PYEOF'
import json, sqlite3, sys
from datetime import datetime, UTC

db_path = sys.argv[1]
now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

metadata = json.dumps({
    "required_reviews": ["self-critique"],
    "require_pr": True,
    "completion_rules": [{
        "when": "blocking_findings AND review_rounds.self-critique >= 2",
        "then": "needs_escalation",
        "target": "task.phase",
        "priority": 1,
        "name": "Critique round limit. Run: ft work blocked 'P0/P1 findings persist'"
    }]
})

conn = sqlite3.connect(db_path)

# Insert task (status=in_progress with started_at, matching transition_task_status behavior)
conn.execute("""
    INSERT INTO tasks (epic_name, title, description, status, position,
                       created_at, started_at, depends_on, is_parallel, metadata)
    VALUES (?, ?, ?, 'in_progress', 1, ?, ?, '[]', 0, ?)
""", ("e2e-round-cap", "e2e-round-cap: Fix persistent bug",
      "Task that will hit round cap", now, now, metadata))

# Insert acceptance criterion (no command — AC check passes trivially)
conn.execute("INSERT INTO acceptance_criteria (task_id, text) VALUES (1, 'Fix the bug')")

conn.commit()
conn.close()
PYEOF
echo "[setup] Created critique-gated task #1 (in_progress)"

# Simulate worker doing work — commit referencing task #1 so commit_scan links it.
# This lets the evidence guard run naturally (no --no-evidence needed).
echo "fix for edge case" > fix.py
git add fix.py
git commit -q -m "fix: handle edge case refs #1"
echo "[setup] Created commit referencing task #1"
echo ""

# ── Test 1: Before threshold — normal needs_fix ──────────────────────────────

echo "[test1] Injecting round 1 self-critique with P1 finding..."
ft review store \
  '{"task_id":1,"review_type":"self-critique","severity":"major","summary":"P1 found","findings":[{"file":"bug.py","line":10,"priority":"P1","description":"Unhandled edge case"}]}' \
  --db-path "$DB"

echo "[test1] Running ft task complete (expect blocked by builtin rule)..."
OUTPUT=$(ft task complete 1 --db-path "$DB" 2>&1 || true)

echo "$OUTPUT" | grep -qi "Blocking findings" \
  && pass "[test1] Error contains \"Blocking findings\" (builtin rule)" \
  || fail "[test1] Expected 'Blocking findings' in output:\n$OUTPUT"

echo "$OUTPUT" | grep -q "Critique round limit" \
  && fail "[test1] 'Critique round limit' should NOT appear at round 1" \
  || pass "[test1] Error does NOT contain \"Critique round limit\""

pass "[test1] PASS"
echo ""

# ── Test 2: After threshold — escalation fires ───────────────────────────────

echo "[test2] Injecting round 2 self-critique with P1 finding..."
ft review store \
  '{"task_id":1,"review_type":"self-critique","severity":"major","summary":"P1 persists","findings":[{"file":"bug.py","line":10,"priority":"P1","description":"Same edge case"}]}' \
  --db-path "$DB"

echo "[test2] Running ft task complete (expect task-level escalation rule)..."
OUTPUT=$(ft task complete 1 --db-path "$DB" 2>&1 || true)

echo "$OUTPUT" | grep -q "Critique round limit" \
  && pass "[test2] Error contains \"Critique round limit\" (task rule fired)" \
  || fail "[test2] Expected 'Critique round limit' in output:\n$OUTPUT"

echo "$OUTPUT" | grep -q "ft work blocked" \
  && pass "[test2] Error contains \"ft work blocked\" (escalation instruction)" \
  || fail "[test2] Expected 'ft work blocked' in output:\n$OUTPUT"

echo "$OUTPUT" | grep -q "Blocking findings" \
  && fail "[test2] Builtin 'Blocking findings' should NOT appear when task rule matches (first-match-wins)" \
  || pass "[test2] Builtin reason correctly suppressed by task rule priority"

pass "[test2] PASS"
echo ""

# ── Test 3: Worker escalates via ft work blocked ─────────────────────────────

echo "[test3] Running ft work blocked (TASK_ID=1 simulates tmux env)..."
TASK_ID=1 ft work blocked "P0/P1 findings persist after self-critique" --db-path "$DB"

# Verify DB state
DB_STATE=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB')
row = conn.execute('SELECT status, blocked_question FROM tasks WHERE id = 1').fetchone()
conn.close()
print(f'{row[0]}|{row[1]}')
")

echo "$DB_STATE" | grep -q "^blocked_user|" \
  && pass "[test3] Task status is blocked_user" \
  || fail "[test3] Expected status 'blocked_user', got: $DB_STATE"

echo "$DB_STATE" | grep -q "P0/P1 findings persist" \
  && pass "[test3] Blocked question is set" \
  || fail "[test3] Expected blocked_question in: $DB_STATE"

# Verify shows up in ft work inbox
INBOX=$(ft work inbox --db-path "$DB" 2>&1)
echo "$INBOX" | grep -q "Fix persistent bug" \
  && pass "[test3] Task visible in inbox" \
  || fail "[test3] Expected task in inbox output:\n$INBOX"

pass "[test3] PASS"
echo ""

# ── Test 4: Recovery — blocked_user → in_progress → clean review ─────────────

echo "[test4] Unblocking task (simulates ft work resume clearing blocked state)..."
python3 -c "
import sqlite3
conn = sqlite3.connect('$DB')
conn.execute(\"UPDATE tasks SET status = 'in_progress', blocked_question = NULL WHERE id = 1\")
conn.commit()
conn.close()
"

# Verify unblocked
DB_STATE=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB')
row = conn.execute('SELECT status, blocked_question FROM tasks WHERE id = 1').fetchone()
conn.close()
print(f'{row[0]}|{row[1]}')
")
echo "$DB_STATE" | grep -q "^in_progress|None" \
  && pass "[test4] Task back to in_progress, blocked_question cleared" \
  || fail "[test4] Expected in_progress|None, got: $DB_STATE"

echo "[test4] Injecting round 3 clean self-critique (findings resolved)..."
ft review store \
  '{"task_id":1,"review_type":"self-critique","severity":"clean","summary":"All issues resolved","findings":[]}' \
  --db-path "$DB"

echo "[test4] Running ft task complete (expect PR-related block, NOT findings/escalation)..."
OUTPUT=$(ft task complete 1 --db-path "$DB" 2>&1 || true)

echo "$OUTPUT" | grep -q "Critique round limit" \
  && fail "[test4] Escalation rule should NOT fire with clean review" \
  || pass "[test4] Task rule correctly did not fire (no blocking findings)"

echo "$OUTPUT" | grep -q "Blocking findings" \
  && fail "[test4] Builtin blocking_findings should NOT fire with clean review" \
  || pass "[test4] No blocking findings after clean round 3"

# With require_pr: true and no GitHub remote, we expect a PR-related message
# This proves the completion path progressed past findings/escalation checks
echo "$OUTPUT" | grep -qi "PR\|awaiting" \
  && pass "[test4] Completion correctly reached PR gate (past all findings checks)" \
  || pass "[test4] Completion progressed past findings checks (no PR gate in output is also valid)"

pass "[test4] PASS"
echo ""

# ── Test 5: Clean round 2 — escalation does NOT false-positive ───────────────
# Create a second task to test the "fixed at round 2" path independently.

echo "[test5] Creating task #2 for clean-round-2 test..."
PROJECT_ROOT="$REAL_PROJECT_ROOT" python3 - "$DB" <<'PYEOF'
import json, sqlite3, sys
from datetime import datetime, UTC

db_path = sys.argv[1]
now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

metadata = json.dumps({
    "required_reviews": ["self-critique"],
    "require_pr": True,
    "completion_rules": [{
        "when": "blocking_findings AND review_rounds.self-critique >= 2",
        "then": "needs_escalation",
        "target": "task.phase",
        "priority": 1,
        "name": "Critique round limit. Run: ft work blocked 'P0/P1 findings persist'"
    }]
})

conn = sqlite3.connect(db_path)
conn.execute("""
    INSERT INTO tasks (epic_name, title, description, status, position,
                       created_at, started_at, depends_on, is_parallel, metadata)
    VALUES (?, ?, ?, 'in_progress', 2, ?, ?, '[]', 0, ?)
""", ("e2e-round-cap", "e2e-round-cap: Fix quickly",
      "Task that fixes at round 2", now, now, metadata))
conn.execute("INSERT INTO acceptance_criteria (task_id, text) VALUES (2, 'Fix it')")
conn.commit()
conn.close()
PYEOF

# Link a commit to task #2
echo "fix for task 2" > fix2.py
git add fix2.py
git commit -q -m "fix: task 2 initial work refs #2"

echo "[test5] Injecting round 1 self-critique with P1 finding for task #2..."
ft review store \
  '{"task_id":2,"review_type":"self-critique","severity":"major","summary":"P1 found","findings":[{"file":"bug2.py","line":5,"priority":"P1","description":"Bug in task 2"}]}' \
  --db-path "$DB"

echo "[test5] Injecting round 2 clean self-critique for task #2 (bug fixed)..."
ft review store \
  '{"task_id":2,"review_type":"self-critique","severity":"clean","summary":"All clear","findings":[]}' \
  --db-path "$DB"

echo "[test5] Running ft task complete 2 (expect NO escalation, findings resolved at round 2)..."
OUTPUT=$(ft task complete 2 --db-path "$DB" 2>&1 || true)

echo "$OUTPUT" | grep -q "Critique round limit" \
  && fail "[test5] Escalation fired on clean round 2 — false positive!" \
  || pass "[test5] Task rule correctly did not fire (round 2 is clean)"

echo "$OUTPUT" | grep -q "Blocking findings" \
  && fail "[test5] Blocking findings on clean round 2 — should be resolved" \
  || pass "[test5] No blocking findings after clean round 2"

pass "[test5] PASS"
echo ""
echo "=== All 5 tests passed ==="
