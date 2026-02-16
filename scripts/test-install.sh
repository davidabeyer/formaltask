#!/usr/bin/env bash
# test-install.sh — Simulates a new user installing formaltask from GitHub.
#
# Creates an isolated temp directory with a fresh venv, installs from the
# specified source (GitHub URL, local path, or PyPI), and runs smoke tests.
#
# Usage:
#   ./scripts/test-install.sh                  # Install from local checkout
#   ./scripts/test-install.sh --from github    # Install from GitHub
#   ./scripts/test-install.sh --from pypi      # Install from PyPI (when published)
#   ./scripts/test-install.sh --keep           # Don't delete temp dir on success
#
# Exit codes:
#   0 — All checks passed
#   1 — Install or smoke test failed

set -euo pipefail

# --- Configuration ---
GITHUB_URL="git+https://github.com/davidabeyer/formaltask.git"
LOCAL_PATH="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="local"
KEEP=false
INSTALL_EXTRAS=""  # e.g. "[tui,llm]" for optional deps

# --- Parse args ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --from)    SOURCE="$2"; shift 2 ;;
        --keep)    KEEP=true; shift ;;
        --extras)  INSTALL_EXTRAS="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,/^$/s/^# //p' "$0"
            exit 0
            ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; FAILURES=$((FAILURES + 1)); }
info() { echo -e "${YELLOW}....${NC} $1"; }

FAILURES=0

# --- Create isolated environment ---
# Force /tmp (not $TMPDIR) — macOS $TMPDIR is /var/folders/... which
# triggers BLOCKED_SYSTEM_DIRS validation in validate_user_db_path.
WORKDIR=$(mktemp -d "/tmp/formaltask-install-test.XXXXXX")
info "Work directory: $WORKDIR"

cleanup() {
    if $KEEP; then
        info "Keeping work directory: $WORKDIR"
    else
        rm -rf "$WORKDIR"
        info "Cleaned up $WORKDIR"
    fi
}
trap cleanup EXIT

# --- Create fresh venv ---
info "Creating virtual environment..."
python3 -m venv "$WORKDIR/venv"

# Use venv binaries directly (avoids pyenv shim interference)
VENV_PYTHON="$WORKDIR/venv/bin/python3"
VENV_PIP="$WORKDIR/venv/bin/pip"
VENV_BIN="$WORKDIR/venv/bin"

if [[ ! -x "$VENV_PYTHON" ]]; then
    fail "Venv python not found at $VENV_PYTHON"
    exit 1
fi
pass "Virtual environment created"

# --- Install ---
info "Installing formaltask (source: $SOURCE)..."
case $SOURCE in
    local)
        "$VENV_PIP" install -q "${LOCAL_PATH}${INSTALL_EXTRAS}" 2>&1 | tail -3
        ;;
    github)
        "$VENV_PIP" install -q "${GITHUB_URL}${INSTALL_EXTRAS}" 2>&1 | tail -3
        ;;
    pypi)
        "$VENV_PIP" install -q "formaltask${INSTALL_EXTRAS}" 2>&1 | tail -3
        ;;
    *)
        echo "Unknown source: $SOURCE (use local, github, or pypi)"
        exit 1
        ;;
esac

if [[ $? -eq 0 ]]; then
    pass "pip install succeeded"
else
    fail "pip install failed"
    exit 1
fi

# --- Smoke Tests ---
echo ""
echo "=== Smoke Tests ==="

# 1. CLI entry points exist
info "Checking CLI entry points..."
if [[ -x "$VENV_BIN/ft" ]]; then
    pass "ft command found"
else
    fail "ft command not found in venv"
fi

if [[ -x "$VENV_BIN/formaltask" ]]; then
    pass "formaltask command found"
else
    fail "formaltask command not found in venv"
fi

# 2. --help works (proves argparse loads, plugins discover)
info "Checking ft --help..."
if "$VENV_BIN/ft" --help &>/dev/null; then
    pass "ft --help exits 0"
else
    fail "ft --help failed"
fi

# 3. Key subcommands are registered
info "Checking subcommand discovery..."
HELP_OUTPUT=$("$VENV_BIN/ft" --help 2>&1)
for cmd in task epic work doctor; do
    if echo "$HELP_OUTPUT" | grep -q "$cmd"; then
        pass "Subcommand '$cmd' registered"
    else
        fail "Subcommand '$cmd' not found in --help"
    fi
done

# 4. Schema SQL is accessible (importlib.resources)
info "Checking packaged schema..."
SCHEMA_CHECK=$("$VENV_PYTHON" -c "
from importlib.resources import files
sql = files('formaltask.data').joinpath('schema.sql').read_text()
print(f'OK: {len(sql)} bytes')
" 2>&1)
if [[ "$SCHEMA_CHECK" == OK:* ]]; then
    pass "Schema SQL accessible via importlib.resources ($SCHEMA_CHECK)"
else
    fail "Schema SQL not accessible: $SCHEMA_CHECK"
fi

# 5. Database initialization in a temp project
info "Checking database initialization..."
FAKE_PROJECT="$WORKDIR/fake-project"
mkdir -p "$FAKE_PROJECT/.claude"
cd "$FAKE_PROJECT"
git init -q .

DB_INIT=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
import os
os.environ['PROJECT_ROOT'] = '$FAKE_PROJECT'
from formaltask.db.schema import ensure_schema_initialized
db_path = '$FAKE_PROJECT/.claude/formaltask.db'
ensure_schema_initialized(db_path)
print('OK')
" 2>&1)
if [[ "$DB_INIT" == *"OK"* ]]; then
    pass "Database initialized successfully"
else
    fail "Database initialization failed: $DB_INIT"
fi

if [[ -f "$FAKE_PROJECT/.claude/formaltask.db" ]]; then
    pass "Database file created at expected path"
else
    fail "Database file not found"
fi

# 6. Core imports work (catches missing deps)
info "Checking core imports..."
IMPORT_CHECK=$("$VENV_PYTHON" -c "
failures = []
modules = [
    'formaltask.cli.pm',
    'formaltask.core',
    'formaltask.db.connection',
    'formaltask.tasks.lifecycle',
    'formaltask.epics.yaml_parser',
    'formaltask.workers.spawner',
]
for mod in modules:
    try:
        __import__(mod)
    except Exception as e:
        failures.append(f'{mod}: {e}')

if failures:
    print('FAIL: ' + '; '.join(failures))
else:
    print(f'OK: {len(modules)} modules imported')
" 2>&1)
if [[ "$IMPORT_CHECK" == OK:* ]]; then
    pass "Core imports succeeded ($IMPORT_CHECK)"
else
    fail "Import failures: $IMPORT_CHECK"
fi

# 7. ft doctor (if it exists and works without full project context)
info "Checking ft doctor..."
DOCTOR_OUT=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_BIN/ft" doctor 2>&1) || true
if echo "$DOCTOR_OUT" | grep -qiE "check|ok|warn|error|diagnostic"; then
    pass "ft doctor runs and produces diagnostic output"
else
    # Doctor may need more context — not a hard failure
    info "ft doctor output unclear (may need full project context): $(echo "$DOCTOR_OUT" | head -2)"
fi

# ======================================================================
# Workflow Tests — exercises the full planning lifecycle against the DB
# ======================================================================
echo ""
echo "=== Workflow Tests ==="

DB_PATH="$FAKE_PROJECT/.claude/formaltask.db"
FT="$VENV_BIN/ft"

# Helper: run ft command with PROJECT_ROOT pointed at fake project
run_ft() {
    PROJECT_ROOT="$FAKE_PROJECT" "$FT" "$@"
}

# 8. Create an epic
info "Creating epic..."
CREATE_OUT=$(run_ft epic create smoke-test "Verify install workflow" --skip-review 2>&1)
if echo "$CREATE_OUT" | grep -q "smoke-test"; then
    pass "ft epic create succeeded"
else
    fail "ft epic create failed: $CREATE_OUT"
fi

# 9. List epics (verify it shows up)
info "Listing epics..."
LIST_OUT=$(run_ft epic list 2>&1)
if echo "$LIST_OUT" | grep -q "smoke-test"; then
    pass "ft epic list shows created epic"
else
    fail "ft epic list missing epic: $LIST_OUT"
fi

# 10. Add a task to the epic
info "Adding task..."
ADD_OUT=$(run_ft task add smoke-test "Verify install works" "Smoke test task" \
    --criteria "CLI exits 0" --criteria "Task appears in list" 2>&1)
if echo "$ADD_OUT" | grep -qE "Added task|task_id"; then
    pass "ft task add succeeded"
else
    fail "ft task add failed: $ADD_OUT"
fi

# 11. Add a second task with dependency on first
info "Adding dependent task..."
ADD2_OUT=$(run_ft task add smoke-test "Second task" "Depends on first" \
    --criteria "Runs after first" --depends-on 1 2>&1)
if echo "$ADD2_OUT" | grep -qE "Added task|task_id"; then
    pass "ft task add with dependency succeeded"
else
    fail "ft task add with dependency failed: $ADD2_OUT"
fi

# 12. Show task detail
info "Showing task..."
SHOW_OUT=$(run_ft task show 1 2>&1)
if echo "$SHOW_OUT" | grep -q "Verify install works"; then
    pass "ft task show displays task title"
else
    fail "ft task show failed: $SHOW_OUT"
fi

# 13. Show task with dependency tree
info "Showing task deps..."
DEPS_OUT=$(run_ft task show 2 --deps 2>&1)
if echo "$DEPS_OUT" | grep -qE "Depends on|dependencies"; then
    pass "ft task show --deps displays dependency info"
else
    fail "ft task show --deps failed: $DEPS_OUT"
fi

# 14. Task list for epic
info "Listing tasks..."
TLIST_OUT=$(run_ft task list smoke-test 2>&1)
if echo "$TLIST_OUT" | grep -q "Verify install works" && echo "$TLIST_OUT" | grep -q "Second task"; then
    pass "ft task list shows both tasks"
else
    fail "ft task list failed: $TLIST_OUT"
fi

# 15. Planning state — begin_stage writes to DB
info "Testing planning state..."
PLAN_STATE=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
from formaltask.epics.planning import begin_stage, load_state

db = '$DB_PATH'
# Simulate plan -> critique -> revise cycle
r1 = begin_stage('smoke-test', 'plan', db)
r2 = begin_stage('smoke-test', 'critique', db)
r3 = begin_stage('smoke-test', 'revise-plan', db)
r4 = begin_stage('smoke-test', 'critique', db)

state = load_state('smoke-test', db)
stage = state['stage']
loops = state['loops']

# Verify state
assert r1 == 1, f'plan round should be 1, got {r1}'
assert r2 == 1, f'critique round 1 should be 1, got {r2}'
assert r4 == 2, f'critique round 2 should be 2, got {r4}'
assert stage == 'critique', f'current stage should be critique, got {stage}'
assert loops['plan'] == 1, f'plan loops should be 1, got {loops[\"plan\"]}'
assert loops['critique'] == 2, f'critique loops should be 2, got {loops[\"critique\"]}'
assert loops['revise-plan'] == 1, f'revise loops should be 1, got {loops[\"revise-plan\"]}'
print(f'OK: stage={stage} loops={loops}')
" 2>&1)
if [[ "$PLAN_STATE" == OK:* ]]; then
    pass "Planning state lifecycle works ($PLAN_STATE)"
else
    fail "Planning state failed: $PLAN_STATE"
fi

# 16. Plan documents table — verify writes
info "Testing plan document storage..."
PLAN_DOC=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
from formaltask.db.connection import DatabaseConnection
from datetime import datetime, UTC

db = '$DB_PATH'
with DatabaseConnection(db) as conn:
    conn.execute(
        'INSERT INTO plan_documents (epic_name, doc_type, path, status, created_at) VALUES (?, ?, ?, ?, ?)',
        ('smoke-test', 'Plan', '/tmp/fake-plan.md', 'active', datetime.now(UTC).isoformat())
    )
    conn.execute(
        'INSERT INTO plan_documents (epic_name, doc_type, path, status, created_at) VALUES (?, ?, ?, ?, ?)',
        ('smoke-test', 'Critique', '/tmp/fake-critique.md', 'active', datetime.now(UTC).isoformat())
    )

with DatabaseConnection(db) as conn:
    rows = conn.execute(
        'SELECT doc_type, path FROM plan_documents WHERE epic_name = ? ORDER BY id', ('smoke-test',)
    ).fetchall()
    assert len(rows) == 2, f'Expected 2 plan docs, got {len(rows)}'
    assert rows[0][0] == 'Plan', f'First doc should be Plan, got {rows[0][0]}'
    assert rows[1][0] == 'Critique', f'Second doc should be Critique, got {rows[1][0]}'
    print(f'OK: {len(rows)} plan documents stored')
" 2>&1)
if [[ "$PLAN_DOC" == OK:* ]]; then
    pass "Plan document storage works ($PLAN_DOC)"
else
    fail "Plan document storage failed: $PLAN_DOC"
fi

# 17. Epic decompose from spec YAML files
info "Testing epic decompose..."
SPEC_DIR="$FAKE_PROJECT/specs"
mkdir -p "$SPEC_DIR"

# Create a second epic for decompose test (avoid conflict with manually-added tasks)
run_ft epic create decompose-test "Test epic decompose" --skip-review &>/dev/null

cat > "$SPEC_DIR/task-001-first.yaml" << 'SPECEOF'
title: "Implement widget"
summary: "Build the widget component from scratch"
context: "The project needs a reusable widget for the dashboard"
implementation:
  - "Create widget module"
  - "Add render method"
acceptance_criteria:
  - "Widget renders correctly"
  - "Tests pass"
testing:
  - "Unit test widget render"
SPECEOF

cat > "$SPEC_DIR/task-002-second.yaml" << 'SPECEOF'
title: "Add widget tests"
summary: "Write comprehensive tests for the widget"
context: "Widget was implemented in task 1, needs test coverage"
implementation:
  - "Write unit tests"
  - "Add integration test"
acceptance_criteria:
  - "Coverage above 80%"
testing:
  - "Run pytest with coverage"
depends_on: [1]
SPECEOF

DECOMPOSE_OUT=$(run_ft epic decompose decompose-test "$SPEC_DIR" 2>&1)
if echo "$DECOMPOSE_OUT" | grep -qE "Created [0-9]+ tasks"; then
    pass "ft epic decompose created tasks from specs"
else
    fail "ft epic decompose failed: $DECOMPOSE_OUT"
fi

# Verify decomposed tasks are visible
DTASKS_OUT=$(run_ft task list decompose-test 2>&1)
if echo "$DTASKS_OUT" | grep -q "Implement widget" && echo "$DTASKS_OUT" | grep -q "Add widget tests"; then
    pass "Decomposed tasks visible in task list"
else
    fail "Decomposed tasks not found: $DTASKS_OUT"
fi

# 18. Work list (spawnable tasks) — should show ready tasks
info "Testing work list..."
WORK_OUT=$(run_ft work list 2>&1)
if echo "$WORK_OUT" | grep -qE "Ready|open|No open tasks|Blocked"; then
    pass "ft work list runs without error"
else
    fail "ft work list failed: $WORK_OUT"
fi

# 19. JSON output mode
info "Testing JSON output..."
JSON_OUT=$(run_ft --json epic list 2>&1)
if echo "$JSON_OUT" | "$VENV_PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert d['success']; print(f'OK: {len(d[\"data\"][\"epics\"])} epics')" 2>&1; then
    pass "JSON output mode works"
else
    fail "JSON output parsing failed: $JSON_OUT"
fi

# 20. Duplicate epic rejection (idempotency check)
info "Testing duplicate epic rejection..."
DUP_OUT=$(run_ft epic create smoke-test "Duplicate" --skip-review 2>&1) || true
if echo "$DUP_OUT" | grep -qiE "error|already|unique|integrity"; then
    pass "Duplicate epic correctly rejected"
else
    fail "Duplicate epic not rejected: $DUP_OUT"
fi

# ======================================================================
# Worker Auto-Unblock Tests — exercises the blocker→resume flow
# ======================================================================
echo ""
echo "=== Worker Auto-Unblock Tests ==="

# 21. Full blocker lifecycle: report → block → complete → auto-unblock
info "Testing blocker task auto-unblock lifecycle..."
UNBLOCK_TEST=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
import json, sqlite3

db = '$DB_PATH'

# --- Setup: create worker epic and tasks ---
conn = sqlite3.connect(db)

# Create epic for this test
conn.execute(
    'INSERT OR IGNORE INTO epics (name, description, created_at) VALUES (?, ?, ?)',
    ('unblock-test', 'Test auto-unblock', '2025-01-01T00:00:00Z')
)

# Task 100: the 'worker' task — currently in_progress
conn.execute(
    '''INSERT INTO tasks (id, epic_name, title, description, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?)''',
    (100, 'unblock-test', 'Worker task', 'The main worker', 'in_progress', '2025-01-01T00:00:00Z')
)

# Simulate: worker runs 'ft work blocked' — sets status to blocked_user
conn.execute(
    \"\"\"UPDATE tasks SET status = 'blocked_user', blocked_question = 'CI is broken, need fix'
       WHERE id = 100\"\"\"
)
conn.commit()

# Verify worker is blocked
row = conn.execute('SELECT status, blocked_question FROM tasks WHERE id = 100').fetchone()
assert row[0] == 'blocked_user', f'Expected blocked_user, got {row[0]}'
assert row[1] == 'CI is broken, need fix', f'Wrong question: {row[1]}'

# Simulate: another worker creates blocker task (ft work report)
metadata = json.dumps({
    'task_type': 'blocker',
    'source_task_id': 100,
    'required_reviews': ['self-critique'],
})
conn.execute(
    '''INSERT INTO tasks (id, epic_name, title, description, status, metadata, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)''',
    (200, 'unblock-test', 'Fix CI', 'Fix the broken CI', 'in_progress', metadata, '2025-01-01T00:00:00Z')
)
conn.commit()

# Verify blocker task has correct metadata
row = conn.execute('SELECT metadata FROM tasks WHERE id = 200').fetchone()
meta = json.loads(row[0])
assert meta['task_type'] == 'blocker', f'Wrong task_type: {meta[\"task_type\"]}'
assert meta['source_task_id'] == 100, f'Wrong source: {meta[\"source_task_id\"]}'

# Complete the blocker task
conn.execute(\"\"\"UPDATE tasks SET status = 'completed' WHERE id = 200\"\"\")
conn.commit()
conn.close()

# Run _auto_unblock_reporter — the function that fires on ft task complete
# Mock resume_worker_in_tmux since we have no tmux/Claude session
import formaltask.cli.commands.task_complete as tc

resume_calls = []
original_resume = tc.resume_worker_in_tmux
tc.resume_worker_in_tmux = lambda tid, msg: resume_calls.append((tid, msg)) or 'task-100'

tc._auto_unblock_reporter(200, db)

tc.resume_worker_in_tmux = original_resume

# Verify resume was called correctly
assert len(resume_calls) == 1, f'Expected 1 resume call, got {len(resume_calls)}'
assert resume_calls[0][0] == 100, f'Resumed wrong task: {resume_calls[0][0]}'
assert 'Blocker task #200 completed' in resume_calls[0][1], f'Wrong message: {resume_calls[0][1]}'

print(f'OK: blocker #200 completed -> resume_worker_in_tmux(100, \"{resume_calls[0][1]}\")')
" 2>&1)
if echo "$UNBLOCK_TEST" | grep -q "^OK:"; then
    pass "Auto-unblock lifecycle works ($(echo "$UNBLOCK_TEST" | grep "^OK:"))"
else
    fail "Auto-unblock lifecycle failed: $UNBLOCK_TEST"
fi

# 22. Auto-unblock fallback when tmux unavailable
info "Testing auto-unblock fallback (no tmux)..."
FALLBACK_TEST=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
import json, sqlite3

db = '$DB_PATH'

# Reset task 100 to blocked_user for fallback test
conn = sqlite3.connect(db)
conn.execute(\"\"\"UPDATE tasks SET status = 'blocked_user', blocked_question = 'Still broken' WHERE id = 100\"\"\")
conn.commit()
conn.close()

import formaltask.cli.commands.task_complete as tc

# Mock resume to raise (simulating no tmux session)
original_resume = tc.resume_worker_in_tmux
tc.resume_worker_in_tmux = lambda tid, msg: (_ for _ in ()).throw(RuntimeError('no tmux'))

tc._auto_unblock_reporter(200, db)

tc.resume_worker_in_tmux = original_resume

# Verify fallback: status cleared to in_progress, blocked_question nulled
conn = sqlite3.connect(db)
row = conn.execute('SELECT status, blocked_question FROM tasks WHERE id = 100').fetchone()
conn.close()

assert row[0] == 'in_progress', f'Expected in_progress after fallback, got {row[0]}'
assert row[1] is None, f'blocked_question should be None, got {row[1]}'
print('OK: fallback cleared blocked state -> in_progress, question=None')
" 2>&1)
if echo "$FALLBACK_TEST" | grep -q "^OK:"; then
    pass "Auto-unblock fallback works ($(echo "$FALLBACK_TEST" | grep "^OK:"))"
else
    fail "Auto-unblock fallback failed: $FALLBACK_TEST"
fi

# 23. Non-blocker task completion does NOT trigger auto-unblock
info "Testing non-blocker is no-op..."
NOOP_TEST=$(PROJECT_ROOT="$FAKE_PROJECT" "$VENV_PYTHON" -c "
import sqlite3

db = '$DB_PATH'

# Reset: task 100 back to blocked_user
conn = sqlite3.connect(db)
conn.execute(\"\"\"UPDATE tasks SET status = 'blocked_user', blocked_question = 'waiting' WHERE id = 100\"\"\")
# Task 1 is a regular task (no blocker metadata)
conn.execute(\"\"\"UPDATE tasks SET status = 'completed' WHERE id = 1\"\"\")
conn.commit()
conn.close()

import formaltask.cli.commands.task_complete as tc
resume_calls = []
original = tc.resume_worker_in_tmux
tc.resume_worker_in_tmux = lambda tid, msg: resume_calls.append((tid, msg))

# Complete a non-blocker task — should NOT trigger resume
tc._auto_unblock_reporter(1, db)
tc.resume_worker_in_tmux = original

assert len(resume_calls) == 0, f'Expected 0 resume calls for non-blocker, got {len(resume_calls)}'

# Task 100 should still be blocked
conn = sqlite3.connect(db)
row = conn.execute('SELECT status FROM tasks WHERE id = 100').fetchone()
conn.close()
assert row[0] == 'blocked_user', f'Non-blocker should not touch task 100, status is {row[0]}'

print('OK: non-blocker completion is no-op (0 resume calls)')
" 2>&1)
if [[ "$NOOP_TEST" == OK:* ]]; then
    pass "Non-blocker is no-op ($NOOP_TEST)"
else
    fail "Non-blocker no-op test failed: $NOOP_TEST"
fi

# --- Summary ---
echo ""
echo "=== Results ==="
INSTALLED_VERSION=$("$VENV_PYTHON" -c "import formaltask; print(getattr(formaltask, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
info "Installed version: $INSTALLED_VERSION"
info "Python: $("$VENV_PYTHON" --version)"
info "Source: $SOURCE"

if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}All smoke tests passed.${NC}"
    exit 0
else
    echo -e "${RED}${FAILURES} test(s) failed.${NC}"
    exit 1
fi
