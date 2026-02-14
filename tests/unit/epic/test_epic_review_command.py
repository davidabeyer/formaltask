"""Tests for pm-epic-review command.

Following TDD approach: write test first, then implement.
"""

import sqlite3
from argparse import Namespace

from formaltask.tasks.lifecycle import transition_task_status
from tests.conftest import make_valid_review_findings

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_epic_review_returns_status_dict(db_path, repo):
    """Test epic_review() returns dict with review status."""
    # Given: An epic with completed tasks
    from formaltask.cli.commands.epic_review import epic_review

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create and complete 2 tasks
    from tests.conftest import make_valid_review

    task1_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Commit 1")
    repo.complete_task(task1_id, make_valid_review(approved=True, summary="Good"))

    task2_id = repo.create_task("test-epic", "Task 2", "Second", ["Criterion 1"])
    transition_task_status(db_path, task2_id, "in_progress")
    repo.link_commit(task2_id, "def456", "Commit 2")
    repo.complete_task(task2_id, make_valid_review(approved=True, summary="Good"))

    # When: Running epic-review (without code review runner for now)
    result = epic_review(epic_name="test-epic", db_path=db_path)

    # Then: Should return status dict with required fields
    assert "ready_to_merge" in result
    assert "p0_count" in result
    assert "p1_count" in result
    assert "p2_count" in result
    assert "total_tasks" in result
    assert "completed_tasks" in result

    # And: Should indicate ready to merge (no P0 issues)
    assert result["ready_to_merge"] is True
    assert result["p0_count"] == 0
    assert result["total_tasks"] == 2
    assert result["completed_tasks"] == 2


def test_epic_review_blocks_merge_with_p0_issues(db_path, repo):
    """Test epic_review() blocks merge when P0 issues found."""
    # Given: An epic with completed tasks that have P0 review findings
    from formaltask.cli.commands.epic_review import epic_review

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create and complete task
    task1_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Commit 1")
    repo.complete_task(task1_id, {"round": 1, "approved": False, "findings": "[]"})

    # Insert task_review with P0 finding
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
            (
                task1_id,
                "code-quality",
                "critical",
                make_valid_review_findings(
                    [
                        {
                            "priority": "P0",
                            "description": "Security vulnerability",
                            "file": "test.py",
                            "line": 42,
                        }
                    ],
                    "P0 security issue found",
                ),
                "2025-01-01T00:00:00Z",
                1,
            ),
        )
        conn.commit()

    # When: Running epic-review
    result = epic_review(epic_name="test-epic", db_path=db_path)

    # Then: Should block merge due to P0 issue
    assert result["ready_to_merge"] is False
    assert result["p0_count"] > 0


class TestRealBehaviors:
    """Real behavior tests for epic_review command.

    Task #1030: Tests that verify actual behavior rather than mock interactions.
    These tests ensure the function correctly processes findings from the database.
    """

    def test_epic_review_counts_p1_and_p2_findings(self, db_path, repo):
        """Verify epic_review correctly counts P1 and P2 findings separately."""
        from formaltask.cli.commands.epic_review import epic_review

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        # Create task
        task_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
        transition_task_status(db_path, task_id, "in_progress")
        repo.link_commit(task_id, "abc123", "Commit 1")

        # Complete the task
        repo.complete_task(task_id, {"round": 1, "approved": True, "findings": "[]"})

        # Insert task_review with P1 and P2 findings
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    "code-quality",
                    "minor",
                    make_valid_review_findings(
                        [
                            {
                                "priority": "P1",
                                "description": "Code smell",
                                "file": "a.py",
                                "line": 10,
                            },
                            {
                                "priority": "P1",
                                "description": "Missing docs",
                                "file": "b.py",
                                "line": 20,
                            },
                            {
                                "priority": "P2",
                                "description": "Style issue",
                                "file": "c.py",
                                "line": 30,
                            },
                        ],
                        "Found minor issues",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            conn.commit()

        # When: Running epic-review
        result = epic_review(epic_name="test-epic", db_path=db_path)

        # Then: Should count P1 and P2 correctly
        assert result["p0_count"] == 0
        assert result["p1_count"] == 2
        assert result["p2_count"] == 1
        assert result["ready_to_merge"] is True  # No P0 = ready

    def test_epic_review_uses_latest_review_round_only(self, db_path, repo):
        """Verify epic_review only counts findings from the latest review round."""
        from formaltask.cli.commands.epic_review import epic_review

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Create and start task
            task_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
            transition_task_status(db_path, task_id, "in_progress")
            repo.link_commit(task_id, "abc123", "Commit 1")

            # Insert round 1 with P0 finding (this should be superseded)
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    "code-quality",
                    "critical",
                    make_valid_review_findings(
                        [
                            {
                                "priority": "P0",
                                "description": "Critical bug",
                                "file": "x.py",
                                "line": 1,
                            }
                        ],
                        "P0 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )

            # Insert round 2 with no P0 findings (this should be used)
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    "code-quality",
                    "minor",
                    make_valid_review_findings(
                        [
                            {
                                "priority": "P2",
                                "description": "Minor style",
                                "file": "x.py",
                                "line": 1,
                            }
                        ],
                        "Issues fixed",
                    ),
                    "2025-01-01T01:00:00Z",
                    2,
                ),
            )

            # Mark task as completed
            cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
            conn.commit()

        # When: Running epic-review
        result = epic_review(epic_name="test-epic", db_path=db_path)

        # Then: Should only count round 2 findings (latest)
        assert result["p0_count"] == 0  # Round 1 P0 should be ignored
        assert result["p2_count"] == 1  # Round 2 P2 should be counted
        assert result["ready_to_merge"] is True

    def test_epic_review_handles_tasks_with_no_reviews(self, db_path, repo):
        """Verify epic_review handles completed tasks that have no review records."""
        from formaltask.cli.commands.epic_review import epic_review

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Create task and mark completed without any review
            # Note: completed_at must be set for get_epic_status to count it as completed
            task_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
            transition_task_status(db_path, task_id, "in_progress")
            cursor.execute(
                "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
                ("2025-01-01T00:00:00Z", task_id),
            )
            conn.commit()

        # When: Running epic-review (should not crash)
        result = epic_review(epic_name="test-epic", db_path=db_path)

        # Then: Should return valid result with zero findings
        assert result["p0_count"] == 0
        assert result["p1_count"] == 0
        assert result["p2_count"] == 0
        assert result["completed_tasks"] == 1
        assert result["ready_to_merge"] is True

    def test_epic_review_aggregates_findings_across_multiple_tasks(self, db_path, repo):
        """Verify epic_review aggregates findings from all completed tasks."""
        from formaltask.cli.commands.epic_review import epic_review

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        # Create task 1 with P0 finding
        task1_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
        transition_task_status(db_path, task1_id, "in_progress")
        repo.link_commit(task1_id, "abc123", "Commit 1")
        repo.complete_task(task1_id, {"round": 1, "approved": False, "findings": "[]"})

        # Create task 2 with P1 finding
        task2_id = repo.create_task("test-epic", "Task 2", "Second", ["Criterion 1"])
        transition_task_status(db_path, task2_id, "in_progress")
        repo.link_commit(task2_id, "def456", "Commit 2")
        repo.complete_task(task2_id, {"round": 1, "approved": True, "findings": "[]"})

        # Create task 3 with P2 finding
        task3_id = repo.create_task("test-epic", "Task 3", "Third", ["Criterion 1"])
        transition_task_status(db_path, task3_id, "in_progress")
        repo.link_commit(task3_id, "ghi789", "Commit 3")
        repo.complete_task(task3_id, {"round": 1, "approved": True, "findings": "[]"})

        # Insert task_reviews
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task1_id,
                    "code-quality",
                    "critical",
                    make_valid_review_findings(
                        [{"priority": "P0", "description": "Critical", "file": "a.py", "line": 1}],
                        "P0 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task2_id,
                    "code-quality",
                    "minor",
                    make_valid_review_findings(
                        [{"priority": "P1", "description": "Minor", "file": "b.py", "line": 1}],
                        "P1 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task3_id,
                    "code-quality",
                    "minor",
                    make_valid_review_findings(
                        [{"priority": "P2", "description": "Style", "file": "c.py", "line": 1}],
                        "P2 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            conn.commit()

        # When: Running epic-review
        result = epic_review(epic_name="test-epic", db_path=db_path)

        # Then: Should aggregate all findings
        assert result["p0_count"] == 1
        assert result["p1_count"] == 1
        assert result["p2_count"] == 1
        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 3
        assert result["ready_to_merge"] is False  # P0 blocks


class TestExecuteMarksReviewed:
    """Tests for execute() marking epic as reviewed when ready_to_merge=True."""

    def test_execute_marks_epic_reviewed_on_success(self, db_path, repo):
        """execute should call mark_reviewed when ready_to_merge=True."""
        from formaltask.cli.commands.epic_review import execute
        from tests.conftest import make_valid_review

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        # Create two tasks - one completed, one open (prevents epic auto-archive)
        task1_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
        repo.create_task("test-epic", "Task 2", "Second", ["Criterion 2"])

        # Complete only the first task with no P0 findings
        transition_task_status(db_path, task1_id, "in_progress")
        repo.link_commit(task1_id, "abc123", "Commit 1")
        repo.complete_task(task1_id, make_valid_review(approved=True, summary="Good"))

        # Execute the command
        args = Namespace(epic_name="test-epic", db_path=db_path)
        execute(args)

        # Verify epic is marked as reviewed
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reviewed_at FROM epics WHERE name = 'test-epic'")
            reviewed_at = cursor.fetchone()[0]
        assert reviewed_at is not None

    def test_execute_does_not_mark_on_failure(self, db_path, repo):
        """execute should NOT call mark_reviewed when ready_to_merge=False."""
        from formaltask.cli.commands.epic_review import execute

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        # Create two tasks - one completed with P0, one open
        task1_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
        repo.create_task("test-epic", "Task 2", "Second", ["Criterion 2"])

        # Complete first task
        transition_task_status(db_path, task1_id, "in_progress")
        repo.link_commit(task1_id, "abc123", "Commit 1")
        repo.complete_task(task1_id, {"round": 1, "approved": False, "findings": "[]"})

        # Insert task_review with P0 findings (blocks merge)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task1_id,
                    "code-quality",
                    "critical",
                    make_valid_review_findings(
                        [
                            {
                                "priority": "P0",
                                "description": "Critical bug",
                                "file": "test.py",
                                "line": 42,
                            }
                        ],
                        "P0 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            conn.commit()

        # Execute the command
        args = Namespace(epic_name="test-epic", db_path=db_path)
        execute(args)

        # Verify epic is NOT marked as reviewed
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reviewed_at FROM epics WHERE name = 'test-epic'")
            reviewed_at = cursor.fetchone()[0]
        assert reviewed_at is None

    def test_execute_returns_nonzero_when_p0_issues_exist(self, db_path, repo):
        """execute should return 1 when ready_to_merge=False due to P0 issues."""
        from formaltask.cli.commands.epic_review import execute

        # Create epic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        # Create task
        task_id = repo.create_task("test-epic", "Task 1", "First", ["Criterion 1"])
        transition_task_status(db_path, task_id, "in_progress")
        repo.link_commit(task_id, "abc123", "Commit 1")
        repo.complete_task(task_id, {"round": 1, "approved": False, "findings": "[]"})

        # Insert task_review with P0 findings (blocks merge)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    "code-quality",
                    "critical",
                    make_valid_review_findings(
                        [
                            {
                                "priority": "P0",
                                "description": "Critical bug",
                                "file": "test.py",
                                "line": 42,
                            }
                        ],
                        "P0 found",
                    ),
                    "2025-01-01T00:00:00Z",
                    1,
                ),
            )
            conn.commit()

        # Execute the command
        args = Namespace(epic_name="test-epic", db_path=db_path)
        result = execute(args)

        # Should return 1 when P0 issues exist
        assert result == 1, f"execute() should return 1 when P0 issues exist, got {result}"
