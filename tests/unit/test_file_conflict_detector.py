"""Tests for file_conflict_detector.py - File conflict detection in specs.

TDD approach: Writing tests one at a time following Red-Green-Refactor cycle.
Reference: Task #1326 - file-conflict-detector-prp.md
"""


class TestExtractFilesFromSpec:
    """Test extracting file mentions from spec text."""

    def test_extracts_modify_pattern(self):
        """Detect 'modify X.py' file mentions in spec text."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        ## Implementation
        - modify hooks/lib/epic_parser.py
        - Add validation logic
        """
        files = extract_files_from_spec(spec_content)

        assert "hooks/lib/epic_parser.py" in files

    def test_extracts_edit_pattern(self):
        """Detect 'edit X.py' file mentions in spec text."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        ## Changes
        - edit hooks/cli/commands/epic_finalize.py
        """
        files = extract_files_from_spec(spec_content)

        assert "hooks/cli/commands/epic_finalize.py" in files

    def test_extracts_create_pattern(self):
        """Detect 'create X.py' file mentions in spec text."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        ## New Files
        - create hooks/lib/new_module.py
        """
        files = extract_files_from_spec(spec_content)

        assert "hooks/lib/new_module.py" in files

    def test_extracts_backtick_paths(self):
        """Detect file paths in backticks."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        The main change is in `hooks/lib/epic_repository.py` which handles
        database operations. Also modify `hooks/tests/conftest.py`.
        """
        files = extract_files_from_spec(spec_content)

        assert "hooks/lib/epic_repository.py" in files
        assert "hooks/tests/conftest.py" in files

    def test_filters_out_urls(self):
        """URLs ending in file extensions should be filtered out."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        Reference: https://github.com/repo/file.py
        Local file: `hooks/lib/parser.py`
        Also see: `https://example.com/script.js`
        """
        files = extract_files_from_spec(spec_content)

        # URLs should not appear
        assert "https://github.com/repo/file.py" not in files
        assert "github.com/repo/file.py" not in files
        assert "https://example.com/script.js" not in files
        # Local files should appear (in backticks)
        assert "hooks/lib/parser.py" in files

    def test_extracts_update_pattern(self):
        """Detect 'update X.py' file mentions in spec text."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        ## Changes
        - update hooks/lib/config.py with new settings
        """
        files = extract_files_from_spec(spec_content)

        assert "hooks/lib/config.py" in files

    def test_empty_string_returns_empty_set(self):
        """Empty spec content returns empty set (graceful handling)."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        files = extract_files_from_spec("")

        assert files == set()

    def test_no_file_mentions_returns_empty_set(self):
        """Spec with text but no file mentions returns empty set."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        ## Overview
        This task involves improving the documentation.
        We need to update several things and modify the approach.

        ## Tasks
        - Review the current implementation
        - Create a plan for improvements
        """
        files = extract_files_from_spec(spec_content)

        assert files == set()

    def test_normalizes_paths(self):
        """Paths are normalized (./foo/bar.py → foo/bar.py)."""
        from formaltask.validators.file_conflict import extract_files_from_spec

        spec_content = """
        - modify ./hooks/lib/parser.py
        - edit hooks/./lib/utils.py
        """
        files = extract_files_from_spec(spec_content)

        # Both should be normalized
        assert "hooks/lib/parser.py" in files
        assert "hooks/lib/utils.py" in files
        # Unnormalized versions should not appear
        assert "./hooks/lib/parser.py" not in files
        assert "hooks/./lib/utils.py" not in files


class TestDetectFileConflicts:
    """Test detecting files touched by multiple tasks."""

    def test_returns_conflicts_for_shared_files(self):
        """Files touched by 2+ tasks are returned as conflicts."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {
                "id": 1,
                "spec_content": "modify hooks/lib/parser.py for task 1",
            },
            {
                "id": 2,
                "spec_content": "edit hooks/lib/parser.py for task 2",
            },
        ]
        conflicts = detect_file_conflicts(tasks)

        # Should have one conflict: parser.py touched by tasks 1 and 2
        assert len(conflicts) >= 1
        conflict_files = [c[0] for c in conflicts]
        assert "hooks/lib/parser.py" in conflict_files

        # Check task IDs
        for file_path, task_ids in conflicts:
            if file_path == "hooks/lib/parser.py":
                assert 1 in task_ids
                assert 2 in task_ids

    def test_no_conflicts_with_disjoint_files(self):
        """Tasks touching different files have no conflicts."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py"},
            {"id": 2, "spec_content": "modify utils.py"},
            {"id": 3, "spec_content": "modify config.py"},
        ]
        conflicts = detect_file_conflicts(tasks)

        assert conflicts == []

    def test_handles_empty_task_list(self):
        """Empty task list returns no conflicts."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        conflicts = detect_file_conflicts([])

        assert conflicts == []

    def test_handles_task_without_spec_content_none(self):
        """Tasks with spec_content=None are skipped gracefully."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py"},
            {"id": 2, "spec_content": None},
        ]
        conflicts = detect_file_conflicts(tasks)

        # No conflict since only task 1 has valid spec_content
        assert conflicts == []

    def test_handles_task_missing_spec_content_key(self):
        """Tasks missing spec_content key are skipped gracefully."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py"},
            {"id": 2},  # Missing spec_content key
        ]
        conflicts = detect_file_conflicts(tasks)

        assert conflicts == []

    def test_handles_task_without_id(self):
        """Tasks missing id are skipped gracefully."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py"},
            {"spec_content": "modify auth.py"},  # Missing id
        ]
        conflicts = detect_file_conflicts(tasks)

        # No conflict - task without id is skipped
        assert conflicts == []

    def test_multiple_tasks_on_same_file(self):
        """3+ tasks touching same file are all reported."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify shared.py"},
            {"id": 2, "spec_content": "edit shared.py"},
            {"id": 3, "spec_content": "update shared.py"},
        ]
        conflicts = detect_file_conflicts(tasks)

        assert len(conflicts) == 1
        conflict_file, task_ids = conflicts[0]
        assert conflict_file == "shared.py"
        assert set(task_ids) == {1, 2, 3}

    def test_multiple_conflicting_files(self):
        """Multiple files with conflicts are all reported."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py and edit utils.py"},
            {"id": 2, "spec_content": "edit auth.py and update config.py"},
            {"id": 3, "spec_content": "modify utils.py and edit config.py"},
        ]
        conflicts = detect_file_conflicts(tasks)

        # auth.py: tasks 1, 2
        # utils.py: tasks 1, 3
        # config.py: tasks 2, 3
        assert len(conflicts) == 3

        conflict_files = {c[0] for c in conflicts}
        assert "auth.py" in conflict_files
        assert "utils.py" in conflict_files
        assert "config.py" in conflict_files

    def test_handles_empty_spec_content(self):
        """Tasks with empty string spec_content are handled gracefully."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [
            {"id": 1, "spec_content": "modify auth.py"},
            {"id": 2, "spec_content": ""},
        ]
        conflicts = detect_file_conflicts(tasks)

        assert conflicts == []

    def test_single_task_no_conflicts(self):
        """Single task has no conflicts by definition."""
        from formaltask.validators.file_conflict import detect_file_conflicts

        tasks = [{"id": 1, "spec_content": "modify auth.py and edit utils.py"}]
        conflicts = detect_file_conflicts(tasks)

        assert conflicts == []


class TestDetectFileOverlapsWithoutDependency:
    """Test detecting risky file overlaps where tasks lack dependency."""

    def test_two_tasks_same_file_no_dependency_returns_overlap(self):
        """Two tasks touching same file with no dependency is risky."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": []},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": []},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == [("auth.py", 1, 2)]

    def test_two_tasks_same_file_with_dependency_returns_empty(self):
        """Two tasks touching same file WITH dependency is safe."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": []},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": [1]},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == []

    def test_two_tasks_same_file_reverse_dependency_returns_empty(self):
        """Dependency in either direction is safe."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": [2]},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": []},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == []

    def test_three_tasks_partial_deps_reports_risky_pairs(self):
        """Only pairs without dependency are reported."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": []},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": [1]},
            {"id": 3, "spec_content": "update `auth.py`", "depends_on": []},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        # 1↔2 has dep, 1↔3 no dep, 2↔3 no dep
        assert ("auth.py", 1, 3) in result
        assert ("auth.py", 2, 3) in result
        assert len(result) == 2

    def test_empty_tasks_returns_empty(self):
        """Empty task list returns empty result."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        result = detect_file_overlaps_without_dependency([])

        assert result == []

    def test_single_task_returns_empty(self):
        """Single task has no pairs to compare."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [{"id": 1, "spec_content": "modify `auth.py`", "depends_on": []}]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == []

    def test_handles_none_depends_on(self):
        """None depends_on is treated as empty list."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": None},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": None},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == [("auth.py", 1, 2)]

    def test_handles_missing_depends_on_key(self):
        """Missing depends_on key is treated as empty list."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`"},
            {"id": 2, "spec_content": "edit `auth.py`"},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == [("auth.py", 1, 2)]

    def test_different_files_no_overlap(self):
        """Tasks touching different files don't produce overlaps."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": []},
            {"id": 2, "spec_content": "modify `utils.py`", "depends_on": []},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == []

    def test_circular_dependency_is_safe(self):
        """Tasks with circular dependency (both depend on each other) are safe."""
        from formaltask.validators.file_conflict import detect_file_overlaps_without_dependency

        tasks = [
            {"id": 1, "spec_content": "modify `auth.py`", "depends_on": [2]},
            {"id": 2, "spec_content": "edit `auth.py`", "depends_on": [1]},
        ]
        result = detect_file_overlaps_without_dependency(tasks)

        assert result == []
