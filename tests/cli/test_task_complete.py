"""Unit tests for `_should_skip_review_gates` branch-trust logic."""

from types import SimpleNamespace
from unittest.mock import patch

from formaltask.cli.commands.task_complete import _should_skip_review_gates


def _git_result(stdout: str, returncode: int = 0):
    return SimpleNamespace(stdout=stdout, returncode=returncode)


def test_skip_on_default_branch():
    with (
        patch(
            "formaltask.git.utils._run_git_command",
            return_value=_git_result("master\n"),
        ),
        patch(
            "formaltask.git.utils.get_default_branch",
            return_value="master",
        ),
    ):
        assert _should_skip_review_gates() == (True, "master")


def test_skip_on_runner_branch():
    with (
        patch(
            "formaltask.git.utils._run_git_command",
            return_value=_git_result("runner/build-foo/builder\n"),
        ),
        patch(
            "formaltask.git.utils.get_default_branch",
            return_value="master",
        ),
    ):
        assert _should_skip_review_gates() == (True, "runner/build-foo/builder")


def test_no_skip_on_feature_branch():
    with (
        patch(
            "formaltask.git.utils._run_git_command",
            return_value=_git_result("feature/some-work\n"),
        ),
        patch(
            "formaltask.git.utils.get_default_branch",
            return_value="master",
        ),
    ):
        assert _should_skip_review_gates() == (False, "feature/some-work")


def test_no_skip_on_detached_head():
    with patch(
        "formaltask.git.utils._run_git_command",
        return_value=_git_result("HEAD\n"),
    ):
        assert _should_skip_review_gates() == (False, "HEAD")
