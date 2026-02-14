"""Tests for fetch_worker_states() function."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from formaltask.apps.dashboard.state import fetch_worker_states
from tests.conftest import make_worker_state


@pytest.fixture
def mocked_state_deps():
    """Mock all external dependencies for fetch_worker_states."""
    with (
        patch("formaltask.apps.dashboard.state.get_prs_for_tasks") as mock_prs,
        patch("formaltask.apps.dashboard.state._fetch_task_metadata_batch") as mock_meta,
        patch("formaltask.apps.dashboard.state.get_worker_state_dict") as mock_state,
        patch("formaltask.apps.dashboard.state.trim_statusline") as mock_trim,
    ):
        yield {
            "get_prs": mock_prs,
            "fetch_meta": mock_meta,
            "get_state": mock_state,
            "trim": mock_trim,
        }


class TestFetchWorkerStates:
    """Tests for fetch_worker_states() - parallel fetching, error handling, caching."""

    def test_empty_sessions_returns_empty_list(self) -> None:
        """Empty sessions list returns empty result immediately."""
        result = fetch_worker_states([], None)
        assert result == []

    def test_single_session_returns_state(self, mocked_state_deps) -> None:
        """Single session fetches and returns one state dict."""
        mocked_state_deps["fetch_meta"].return_value = {42: {"title": "Test task"}}
        mocked_state_deps["get_state"].return_value = make_worker_state(
            task_id=42, session_name="task-42", health_state="running", pane_output="Working on task..."
        )
        mocked_state_deps["trim"].return_value = "Working on task..."

        result = fetch_worker_states([("task-42", 42)], Path("/db"))

        assert len(result) == 1
        assert result[0]["task_id"] == 42
        assert result[0]["health_state"] == "running"
        mocked_state_deps["get_prs"].assert_called_once_with([42])

    def test_skip_pr_fetch_skips_github_api(self, mocked_state_deps) -> None:
        """skip_pr_fetch=True skips expensive GitHub API calls."""
        mocked_state_deps["fetch_meta"].return_value = {}
        mocked_state_deps["get_state"].return_value = make_worker_state(pane_output="")
        mocked_state_deps["trim"].return_value = ""

        fetch_worker_states([("task-1", 1)], Path("/db"), skip_pr_fetch=True)

        mocked_state_deps["get_prs"].assert_not_called()

    def test_oserror_excluded_from_results(self, mocked_state_deps) -> None:
        """OSError during fetch excludes that worker from results."""
        mocked_state_deps["fetch_meta"].return_value = {}
        mocked_state_deps["get_state"].side_effect = OSError("Connection refused")

        result = fetch_worker_states([("task-1", 1)], Path("/db"))

        assert result == []

    def test_partial_failure_returns_successful_states(self, mocked_state_deps) -> None:
        """If one worker fails, others still return successfully."""
        mocked_state_deps["fetch_meta"].return_value = {}

        def side_effect(task_id: int, session_name: str, **kwargs: Any) -> dict:
            if task_id == 1:
                raise OSError("Connection refused")
            return make_worker_state(task_id=task_id, pane_output="ok", health_state="running")

        mocked_state_deps["get_state"].side_effect = side_effect
        mocked_state_deps["trim"].return_value = "ok"

        result = fetch_worker_states([("task-1", 1), ("task-2", 2), ("task-3", 3)], Path("/db"))

        assert len(result) == 2
        task_ids = {r["task_id"] for r in result}
        assert task_ids == {2, 3}

    def test_findings_cached_for_navigation(self, mocked_state_deps) -> None:
        """Findings are fetched and cached in the state dict."""
        mocked_state_deps["fetch_meta"].return_value = {}
        mocked_state_deps["get_state"].return_value = make_worker_state(
            task_id=42, pane_output="Working...", health_state="running"
        )
        mocked_state_deps["trim"].return_value = "Working..."

        with patch(
            "formaltask.apps.dashboard.state.get_findings_with_disposition"
        ) as mock_findings:
            mock_findings.return_value = [{"id": 1, "priority": "P0", "message": "Bug"}]

            result = fetch_worker_states([("task-42", 42)], Path("/db"))

            assert len(result) == 1
            assert result[0]["cached_findings"] == [{"id": 1, "priority": "P0", "message": "Bug"}]

    def test_findings_fetch_failure_graceful_degradation(self, mocked_state_deps) -> None:
        """If findings fetch fails, returns empty list (graceful degradation)."""
        import sqlite3

        mocked_state_deps["fetch_meta"].return_value = {}
        mocked_state_deps["get_state"].return_value = make_worker_state(
            task_id=42, pane_output="", health_state="running"
        )
        mocked_state_deps["trim"].return_value = ""

        with patch(
            "formaltask.apps.dashboard.state.get_findings_with_disposition"
        ) as mock_findings:
            mock_findings.side_effect = sqlite3.Error("Database error")

            result = fetch_worker_states([("task-42", 42)], Path("/db"))

            assert len(result) == 1
            assert result[0]["cached_findings"] == []

    def test_no_db_path_skips_metadata_and_findings(self) -> None:
        """db_path=None skips metadata batch fetch and findings cache."""
        with (
            patch("formaltask.apps.dashboard.state.get_prs_for_tasks"),
            patch("formaltask.apps.dashboard.state.get_worker_state_dict") as mock_state,
            patch("formaltask.apps.dashboard.state.trim_statusline", return_value=""),
        ):
            mock_state.return_value = make_worker_state(pane_output="")

            result = fetch_worker_states([("task-1", 1)], None)

            assert len(result) == 1
            assert "cached_findings" not in result[0]
