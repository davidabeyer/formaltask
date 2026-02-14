"""Tests for github_pr_utils module.

Behavior tests only - import/exists tests removed per Beck's Razor.
"""


def test_get_prs_for_tasks_returns_prinfo_for_merged_pr() -> None:
    """PRInfo.merged=True when mergedAt present."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 42, "headRefName": "task-123", "state": "MERGED", "mergedAt": "2026-01-10"}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    assert 123 in result
    assert result[123].number == 42
    assert result[123].state == "MERGED"
    assert result[123].merged is True


def test_get_prs_for_tasks_returns_prinfo_for_open_pr() -> None:
    """PRInfo.state='OPEN', merged=False for open PRs."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 55, "headRefName": "task-456", "state": "OPEN", "mergedAt": None}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    assert 456 in result
    assert result[456].number == 55
    assert result[456].state == "OPEN"
    assert result[456].merged is False


def test_get_prs_for_tasks_returns_prinfo_for_closed_pr() -> None:
    """PRInfo.state='CLOSED', merged=False for closed PRs."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 77, "headRefName": "task-789", "state": "CLOSED", "mergedAt": None}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    assert 789 in result
    assert result[789].number == 77
    assert result[789].state == "CLOSED"
    assert result[789].merged is False


def test_get_prs_for_tasks_filters_by_task_ids() -> None:
    """Only returns requested task IDs when filter provided."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [
            {"number": 1, "headRefName": "task-100", "state": "OPEN", "mergedAt": None},
            {"number": 2, "headRefName": "task-200", "state": "MERGED", "mergedAt": "2026-01-10"},
            {"number": 3, "headRefName": "task-300", "state": "CLOSED", "mergedAt": None},
        ]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks([100, 300])

    assert 100 in result
    assert 300 in result
    assert 200 not in result


def test_get_pr_for_task_returns_none_for_missing() -> None:
    """Returns None when no PR for task."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_pr_for_task

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 42, "headRefName": "task-123", "state": "OPEN", "mergedAt": None}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_pr_for_task(999)

    assert result is None


def test_cache_returns_cached_result_within_ttl() -> None:
    """Subprocess called once for two calls within TTL."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 42, "headRefName": "task-123", "state": "OPEN", "mergedAt": None}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result) as mock_run:
        result1 = get_prs_for_tasks()
        result2 = get_prs_for_tasks()

    assert mock_run.call_count == 1
    assert result1 == result2


def test_cache_refreshes_after_ttl_expires() -> None:
    """Subprocess called twice after TTL expires."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [{"number": 42, "headRefName": "task-123", "state": "OPEN", "mergedAt": None}]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with (
        patch("formaltask.git.github.subprocess.run", return_value=mock_result) as mock_run,
        patch("formaltask.git.github.time.time") as mock_time,
    ):
        mock_time.return_value = 1000.0
        get_prs_for_tasks()

        mock_time.return_value = 1301.0  # 301 seconds later (TTL is 300s)
        get_prs_for_tasks()

    assert mock_run.call_count == 2


def test_returns_empty_dict_on_timeout() -> None:
    """Empty dict on TimeoutExpired."""
    import subprocess
    from unittest.mock import patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    with patch(
        "formaltask.git.github.subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 30)
    ):
        result = get_prs_for_tasks()

    assert result == {}


def test_returns_empty_dict_on_cli_not_found() -> None:
    """Empty dict on FileNotFoundError (gh CLI not found)."""
    from unittest.mock import patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    with patch(
        "formaltask.git.github.subprocess.run", side_effect=FileNotFoundError("gh not found")
    ):
        result = get_prs_for_tasks()

    assert result == {}


def test_returns_empty_dict_on_invalid_json() -> None:
    """Empty dict on JSONDecodeError."""
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_result = Mock(returncode=0, stdout="not valid json", stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    assert result == {}


def test_returns_empty_dict_on_nonzero_exit() -> None:
    """Empty dict on returncode != 0."""
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_result = Mock(returncode=1, stdout="", stderr="error")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    assert result == {}


def test_skips_malformed_pr_missing_required_fields() -> None:
    """Skips PRs missing number or state fields instead of raising KeyError."""
    import json
    from unittest.mock import Mock, patch

    import formaltask.git.github as gh_mod
    from formaltask.git.github import get_prs_for_tasks

    gh_mod._pr_cache = None
    mock_stdout = json.dumps(
        [
            {"headRefName": "task-123", "state": "OPEN", "mergedAt": None},  # Missing number
            {"number": 42, "headRefName": "task-456", "mergedAt": None},  # Missing state
            {
                "number": 99,
                "headRefName": "task-789",
                "state": "MERGED",
                "mergedAt": "2026-01-10",
            },  # Valid
        ]
    )
    mock_result = Mock(returncode=0, stdout=mock_stdout, stderr="")

    with patch("formaltask.git.github.subprocess.run", return_value=mock_result):
        result = get_prs_for_tasks()

    # Should only have valid PR, not raise KeyError
    assert 123 not in result  # Missing number
    assert 456 not in result  # Missing state
    assert 789 in result
    assert result[789].number == 99
