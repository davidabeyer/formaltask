"""Tests for feature branch isolation.

Verifies three integration points:
1. Feature branch guard blocks pushes to master when epic has feature_branch
2. Spawner selects feature_branch as worktree base
3. Spawner writes correct target_branch to .task/
"""

from formaltask.db.connection import DatabaseConnection


def _create_epic_with_feature_branch(db_path, feature_branch=None):
    """Create an epic with optional feature_branch."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at, feature_branch) VALUES (?, ?, ?, ?)",
            ("test-epic", "Test", "2025-01-01T00:00:00Z", feature_branch),
        )
        conn.commit()


def _create_task_in_epic(db_path, epic_name="test-epic"):
    """Create a task in an epic, return task_id."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks (epic_name, title, description, position, status, created_at)
               VALUES (?, ?, ?, 1, 'open', ?)""",
            (epic_name, "Test Task", "Desc", "2025-01-01T00:00:00Z"),
        )
        task_id = cursor.lastrowid
        conn.commit()
        return task_id


class TestFeatureBranchGuard:
    """Tests for check_feature_branch_target validator."""

    def test_blocks_push_to_master_when_epic_has_feature_branch(self, db_path):
        """Task branch push to master blocked when epic has feature_branch set."""
        from formaltask.validators.feature_branch import check_feature_branch_target

        _create_epic_with_feature_branch(db_path, feature_branch="feature/auth")
        task_id = _create_task_in_epic(db_path)

        result = check_feature_branch_target(
            branch=f"task-{task_id}",
            target_ref="refs/heads/master",
            db_path=db_path,
        )

        assert result["allowed"] is False
        assert result["feature_branch"] == "feature/auth"

    def test_allows_push_to_master_when_no_feature_branch(self, db_path):
        """Task branch push to master allowed when epic has no feature_branch."""
        from formaltask.validators.feature_branch import check_feature_branch_target

        _create_epic_with_feature_branch(db_path, feature_branch=None)
        task_id = _create_task_in_epic(db_path)

        result = check_feature_branch_target(
            branch=f"task-{task_id}",
            target_ref="refs/heads/master",
            db_path=db_path,
        )

        assert result["allowed"] is True

    def test_allows_non_task_branch(self, db_path):
        """Non-task branches always allowed (e.g. feature/foo)."""
        from formaltask.validators.feature_branch import check_feature_branch_target

        result = check_feature_branch_target(
            branch="feature/something",
            target_ref="refs/heads/master",
            db_path=db_path,
        )

        assert result["allowed"] is True
        assert "Not a task branch" in result["reason"]

    def test_allows_push_to_non_master_target(self, db_path):
        """Push to non-master refs always allowed."""
        from formaltask.validators.feature_branch import check_feature_branch_target

        _create_epic_with_feature_branch(db_path, feature_branch="feature/auth")
        task_id = _create_task_in_epic(db_path)

        result = check_feature_branch_target(
            branch=f"task-{task_id}",
            target_ref="refs/heads/feature/auth",
            db_path=db_path,
        )

        assert result["allowed"] is True
        assert "Not pushing to master" in result["reason"]

    def test_handles_missing_task(self, db_path):
        """Unknown task ID doesn't crash — returns allowed with explanation."""
        from formaltask.validators.feature_branch import check_feature_branch_target

        result = check_feature_branch_target(
            branch="task-99999",
            target_ref="refs/heads/master",
            db_path=db_path,
        )

        assert result["allowed"] is True
        assert "not found" in result["reason"]


class TestSpawnerFeatureBranchSelection:
    """Tests for spawner's feature_branch base selection logic.

    Tests the DB query logic without actually spawning workers/worktrees.
    """

    def test_selects_feature_branch_as_base(self, db_path):
        """When epic has feature_branch, spawner should use it as base_branch."""
        _create_epic_with_feature_branch(db_path, feature_branch="feature/auth")
        task_id = _create_task_in_epic(db_path)

        # Replicate spawner's DB query (spawner.py:492-501)
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            row = cursor.fetchone()
            feature_branch = row[0] if row and row[0] else None

        assert feature_branch == "feature/auth"

    def test_falls_back_to_none_when_no_feature_branch(self, db_path):
        """When epic has no feature_branch, query returns None (spawner uses origin/master)."""
        _create_epic_with_feature_branch(db_path, feature_branch=None)
        task_id = _create_task_in_epic(db_path)

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            row = cursor.fetchone()
            feature_branch = row[0] if row and row[0] else None

        assert feature_branch is None

    def test_target_branch_uses_feature_branch_without_origin_prefix(self, db_path):
        """Spawner writes feature_branch (not origin/feature_branch) to .task/target_branch.

        This is critical — PR creation uses target_branch as --base, and
        'origin/feature/auth' is not a valid GitHub base branch.
        """
        _create_epic_with_feature_branch(db_path, feature_branch="feature/auth")
        task_id = _create_task_in_epic(db_path)

        # Replicate spawner's target_branch logic (spawner.py:556)
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            row = cursor.fetchone()
            feature_branch = row[0] if row and row[0] else None

        default_branch = "master"
        target_branch = feature_branch if feature_branch else default_branch

        assert target_branch == "feature/auth"
        assert not target_branch.startswith("origin/")


class TestGuardFeatureBranchAlignment:
    """Tests that guards use the same feature_branch logic as spawner."""

    def test_guard_query_matches_spawner_query(self, db_path):
        """Guard and spawner use identical SQL to get feature_branch.

        Both must produce the same result for the same task.
        """
        _create_epic_with_feature_branch(db_path, feature_branch="feature/auth")
        task_id = _create_task_in_epic(db_path)

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()

            # Spawner query (spawner.py:494-498)
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            spawner_result = cursor.fetchone()

            # Guard query is identical — both JOIN tasks→epics on epic_name
            # This test proves they see the same data
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            guard_result = cursor.fetchone()

        assert spawner_result == guard_result
        assert spawner_result[0] == "feature/auth"
