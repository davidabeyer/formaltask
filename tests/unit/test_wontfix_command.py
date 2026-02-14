"""Tests for pm wontfix command.

Task #2115: CLI command to mark review findings as wontfix, list existing entries, or clear them.
"""


def test_execute_add_inserts_wontfix_entry(db_path):
    """Execute with file, line, reason, and --task inserts wontfix entry."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    args = argparse.Namespace(
        file="foo.py",
        line=42,
        reason="Pre-existing in legacy code",
        task=123,
        list=False,
        clear=False,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT file, line, reason FROM finding_dispositions WHERE task_id = ?",
            (123,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "foo.py"
        assert row[1] == 42
        assert row[2] == "Pre-existing in legacy code"


def test_execute_list_shows_wontfix_entries(db_path, capsys):
    """Execute with --list shows all wontfix entries for the task."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO finding_dispositions (task_id, file, line, reason) VALUES (?, ?, ?, ?)",
            (123, "foo.py", 42, "Pre-existing code"),
        )
        conn.execute(
            "INSERT INTO finding_dispositions (task_id, file, line, reason) VALUES (?, ?, ?, ?)",
            (123, "bar.py", 100, "Technical debt"),
        )
        conn.commit()

    args = argparse.Namespace(
        file=None,
        line=None,
        reason=None,
        task=123,
        list=True,
        clear=False,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "foo.py:42" in captured.out
    assert "bar.py:100" in captured.out


def test_execute_clear_removes_wontfix_entry(db_path):
    """Execute with --clear removes wontfix entry for file/line."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO finding_dispositions (task_id, file, line, reason) VALUES (?, ?, ?, ?)",
            (123, "foo.py", 42, "Pre-existing code"),
        )
        conn.commit()

    args = argparse.Namespace(
        file="foo.py",
        line=42,
        reason=None,
        task=123,
        list=False,
        clear=True,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM finding_dispositions WHERE task_id = ?",
            (123,),
        )
        count = cursor.fetchone()[0]
        assert count == 0


def test_execute_returns_not_found_when_no_task(db_path, capsys):
    """Execute returns exit code 64 (NOT_FOUND) when no --task and no active session."""
    import argparse

    from formaltask.cli.commands import disposition
    from formaltask.cli.exit_codes import ExitCode

    args = argparse.Namespace(
        file="foo.py",
        line=42,
        reason="Pre-existing code",
        task=None,
        list=False,
        clear=False,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == ExitCode.NOT_FOUND

    captured = capsys.readouterr()
    assert "task" in captured.err.lower() or "task" in captured.out.lower()


def test_execute_returns_usage_error_on_invalid_args(db_path, capsys):
    """Execute returns USAGE_ERROR when file/line given without --reason."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition
    from formaltask.cli.exit_codes import ExitCode

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    args = argparse.Namespace(
        file="foo.py",
        line=42,
        reason=None,
        task=123,
        list=False,
        clear=False,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == ExitCode.USAGE_ERROR

    captured = capsys.readouterr()
    assert "reason" in captured.err.lower()


def test_execute_returns_usage_error_on_clear_without_file(db_path, capsys):
    """Execute returns USAGE_ERROR for --clear without FILE."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition
    from formaltask.cli.exit_codes import ExitCode

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    args = argparse.Namespace(
        file=None,
        line=None,
        reason=None,
        task=123,
        list=False,
        clear=True,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == ExitCode.USAGE_ERROR

    captured = capsys.readouterr()
    assert "clear" in captured.err.lower()


def test_execute_clear_returns_not_found_when_entry_missing(db_path, capsys):
    """Execute with --clear returns NOT_FOUND when no entry exists for file/line."""
    import argparse
    import sqlite3

    from formaltask.cli.commands import disposition
    from formaltask.cli.exit_codes import ExitCode

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (123, "test-epic", "Test task", "Test description", "open", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    args = argparse.Namespace(
        file="nonexistent.py",
        line=999,
        reason=None,
        task=123,
        list=False,
        clear=True,
        needshuman=False,
        fixed=False,
        db_path=db_path,
    )

    exit_code = disposition.execute(args)
    assert exit_code == ExitCode.NOT_FOUND

    captured = capsys.readouterr()
    assert "no entry found" in captured.out.lower()
