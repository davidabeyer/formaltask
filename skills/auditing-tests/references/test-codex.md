# Test Codex

Concrete patterns for antirez-style, Beck-minimal tests. Every test earns its place or gets deleted.

## The 9 Patterns

### 1. Behavior, Not Implementation

```python
# YES
def test_parser_extracts_numbers():
    assert parse("abc123def") == ["123"]  # pragma: allowlist secret

# NO
def test_parser_uses_regex():
    assert parser._internal_regex.pattern == r"\d+"
```

### 2. One Concept Per Test

```python
# YES
def test_empty_list_returns_none():
    assert find_max([]) is None

def test_single_element_returns_it():
    assert find_max([5]) == 5

# NO
def test_find_max():
    assert find_max([]) is None
    assert find_max([5]) == 5
    assert find_max([1, 3, 2]) == 3
```

### 3. Beck's Razor — Delete If Refactor-Fragile

> "Would deleting this test let a real bug slip through?"

- Refactor breaks it but behavior didn't change → **delete**
- Rename/move breaks it but not behavioral change → **delete**
- Only breaks on actual behavior regression → **keep**

### 4. Mock Only at Boundaries

```python
# YES — mock DB, call pure functions directly
def test_validate_email(mock_db):
    result = validate_and_store("bad@", mock_db)
    assert result.errors == ["invalid email"]

# NO — mocking pure functions
def test_process(mock_validator, mock_formatter, mock_db):
    mock_validator.return_value = True
    mock_formatter.return_value = "formatted"
    process("input", mock_validator, mock_formatter, mock_db)
    mock_db.insert.assert_called_once()
```

Boundary = DB, external API, subprocess, filesystem. Everything else: call it directly.

### 5. Name = Specification

```python
# YES
def test_spawn_blocked_task_returns_error():
def test_epic_with_no_tasks_shows_empty():
def test_escalation_section_teaches_blocked_cli_command():

# NO
def test_spawn():
def test_epic():
def test_error_handling():
```

Format: `test_<component>_<scenario>_<expected>`

### 6. Equivalence Classes, Not Exhaustion

```python
# YES — 2 cases cover both branches
@pytest.mark.parametrize("n,expected", [(2, True), (3, False)])
def test_is_even(n, expected):
    assert is_even(n) == expected

# NO — 10 cases for 2 branches
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_is_even(n):
    assert is_even(n) == (n % 2 == 0)
```

Rule: one representative per equivalence class + boundary values.

### 7. Flat Setup (≤5 Lines)

```python
# YES
def test_task_completion(db_path):
    task_id = create_task(db_path, "Test task")
    complete_task(db_path, task_id)
    assert get_task(db_path, task_id)["status"] == "completed"

# NO — setup IS the test
def test_task_completion(db_path, mock_gh, mock_subprocess, tmp_path):
    epic_id = create_epic(db_path, "epic", "desc")
    task_id = create_task(db_path, epic_id, "task", "desc", "spec")
    assign_worker(db_path, task_id, "worker-1")
    start_session(db_path, task_id)
    mock_gh.return_value = {"number": 42}
    mock_subprocess.return_value = CompletedProcess(...)
    # ... actual assertion buried after 10 lines
```

If setup exceeds 5 lines, you're testing at the wrong boundary.

### 8. Real > Fixtures > Mocks

Preference chain:
1. **Real objects** — `db_path` (temp SQLite), actual functions, real files
2. **Fixtures** — `db_with_epic_and_tasks` (pre-populated data)
3. **Mocks** — only for external boundaries (GitHub API, subprocess, network)

```python
# YES — real temp DB
def test_busy_timeout_is_set(self, tmp_path):
    db_path = tmp_path / "test.db"
    with DatabaseConnection(db_path) as conn:
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 5000

# NO — mocking what you can create for real
def test_connection(mock_sqlite):
    mock_sqlite.connect.return_value = MagicMock()
    # Testing the mock, not the code
```

### 9. No Framework Testing

```python
# YES — tests YOUR code
def test_parse_epic_extracts_title():
    result = parse_epic("# My Epic\n...")
    assert result["title"] == "My Epic"

# NO — tests that Python/pytest/SQLite works
def test_dict_has_keys():
    d = {"a": 1}
    assert "a" in d

# NO — tests the test infrastructure
def test_fixture_creates_database(db_path):
    assert db_path.exists()
```

## Severity Scale

| Level | Meaning | Example |
|-------|---------|---------|
| P0 | Tests wrong thing, hides bugs | Mock-only assertions prove nothing about behavior |
| P1 | Implementation-coupled, maintenance cost | Breaks on every refactor but behavior unchanged |
| P2 | Redundant or bloated, CI cost | 10 parameterized cases for 2 branches |
| P3 | Style preference | Could use better name |

## Exemplar Test Files

These score 9/9. Use as reference:

- `tests/unit/worker/test_worker_event_payloads.py` (14 LOC) — Zero setup, real call, one concept
- `tests/unit/test_db_connection.py` (21 LOC) — Real DB, behavior assertion, flat
- `tests/unit/test_escalation_section.py` (30 LOC) — Zero mocking, output property checks
- `tests/unit/test_fake_assertion_detection.py` (31 LOC) — Real file ops, no mocks
- `tests/unit/test_create_session_metadata.py` (36 LOC) — Real filesystem, two clean concepts
