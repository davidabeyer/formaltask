"""Test epic_list command."""

from formaltask.db.connection import DatabaseConnection

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_epic_list_shows_all_non_archived_epics(db_path, repo, capsys):
    """
    RED: Test epic_list displays all non-archived epics with status.

    Should show:
    - Epic names
    - Computed status from epic_status VIEW
    - Task counts (total, completed, in_progress)
    - Exclude archived epics by default
    """
    from formaltask.cli.commands.epic_list import epic_list

    # Given: Two epics (one archived)
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("active-epic", "Active epic", "2025-11-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO epics (name, description, created_at, archived_at) VALUES (?, ?, ?, ?)",
            ("archived-epic", "Archived epic", "2025-11-02T00:00:00Z", "2025-11-03T00:00:00Z"),
        )

    # When: Listing epics
    epic_list(db_path=db_path, show_archived=False)

    # Then: Should show active epic (plus master-adhoc from schema)
    captured = capsys.readouterr()
    assert "active-epic" in captured.out
    assert "archived-epic" not in captured.out  # archived should be excluded
    assert "master-adhoc" in captured.out  # auto-created by schema
    assert "Total: 2 epics" in captured.out  # active-epic + master-adhoc


def test_epic_list_shows_archived_when_requested(db_path, repo, capsys):
    """
    RED: Test epic_list shows archived epics when show_archived=True.
    """
    from formaltask.cli.commands.epic_list import epic_list

    # Given: One archived epic
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at, archived_at) VALUES (?, ?, ?, ?)",
            ("archived-epic", "Archived epic", "2025-11-02T00:00:00Z", "2025-11-03T00:00:00Z"),
        )

    # When: Listing epics with show_archived=True
    epic_list(db_path=db_path, show_archived=True)

    # Then: Should show archived epic
    captured = capsys.readouterr()
    assert "archived-epic" in captured.out
    assert "archived" in captured.out  # status should be 'archived'
    assert "Total: 2 epics" in captured.out  # archived-epic + master-adhoc
