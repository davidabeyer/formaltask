"""Tests for hooks/lib/git_utils.py shared utility."""

import subprocess

import pytest

# ============================================================================
# Tests for new git_utils functions (Task #1828)
# ============================================================================


class TestValidateGitArg:
    """Tests for _validate_git_arg() injection prevention."""

    def test_rejects_dangerous_options(self):
        """_validate_git_arg raises ValueError for dangerous options with values."""
        from formaltask.git.utils import _validate_git_arg

        with pytest.raises(ValueError, match="Invalid git argument"):
            _validate_git_arg("--upload-pack=evil")

    def test_accepts_valid_sha(self):
        """_validate_git_arg does not raise for valid SHA-like strings."""
        from formaltask.git.utils import _validate_git_arg

        # Should not raise
        _validate_git_arg("abc123def456")  # pragma: allowlist secret
        _validate_git_arg("HEAD")
        _validate_git_arg("main")

    def test_accepts_standard_git_flags(self):
        """_validate_git_arg allows standard git short flags and safe long flags."""
        from formaltask.git.utils import _validate_git_arg

        # Standard git flags should be allowed
        _validate_git_arg("-e")  # cat-file existence check
        _validate_git_arg("-C")  # directory change
        _validate_git_arg("-n")  # dry-run
        _validate_git_arg("--is-ancestor")  # merge-base option

    def test_accepts_whitelisted_format_options(self):
        """_validate_git_arg allows --format= and --pretty= options."""
        from formaltask.git.utils import _validate_git_arg

        # Format options are whitelisted (safe format specifiers)
        _validate_git_arg("--format=%B")  # Full commit body
        _validate_git_arg("--format=%s")  # Subject line
        _validate_git_arg("--format=%H")  # Full commit hash
        _validate_git_arg("--pretty=%B")  # Alias for --format
        _validate_git_arg("--pretty=oneline")  # Named format


class TestGetGitEnv:
    """Tests for _get_git_env() locale handling."""

    def test_sets_lc_all_c(self):
        """_get_git_env sets LC_ALL=C for consistent output."""
        from formaltask.git.utils import _get_git_env

        env = _get_git_env()
        assert env["LC_ALL"] == "C"


class TestRunGitCommand:
    """Tests for _run_git_command() subprocess wrapper."""

    def test_returns_none_on_timeout(self, monkeypatch):
        """_run_git_command returns None when command times out."""
        from formaltask.git.utils import _run_git_command

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _run_git_command(["status"])
        assert result is None

    def test_returns_completed_process_on_success(self, monkeypatch):
        """_run_git_command returns CompletedProcess on success."""
        from formaltask.git.utils import _run_git_command

        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "HEAD"],
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = _run_git_command(["rev-parse", "HEAD"])
        assert result is not None
        assert result.returncode == 0
        assert result.stdout == "abc123\n"

    def test_validates_arguments(self):
        """_run_git_command validates args for injection prevention."""
        from formaltask.git.utils import _run_git_command

        with pytest.raises(ValueError, match="Invalid git argument"):
            _run_git_command(["--upload-pack=evil", "status"])

    def test_returns_none_on_file_not_found(self, monkeypatch):
        """_run_git_command returns None when git is not found."""
        from formaltask.git.utils import _run_git_command

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _run_git_command(["status"])
        assert result is None


class TestGetHeadSha:
    """Tests for get_head_sha()."""

    def test_returns_sha_on_success(self, monkeypatch):
        """get_head_sha returns 40-char SHA on success."""
        from formaltask.git.utils import get_head_sha

        sha = "a" * 40
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"{sha}\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_head_sha()
        assert result == sha
        assert len(result) == 40

    def test_returns_none_on_error(self, monkeypatch):
        """get_head_sha returns None when not in git repo."""
        from formaltask.git.utils import get_head_sha

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_head_sha()
        assert result is None


class TestCommitExists:
    """Tests for commit_exists()."""

    def test_returns_true_for_existing_commit(self, monkeypatch):
        """commit_exists returns True when commit exists."""
        from formaltask.git.utils import commit_exists

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = commit_exists("abc123")
        assert result is True

    def test_returns_false_for_missing_commit(self, monkeypatch):
        """commit_exists returns False when commit doesn't exist."""
        from formaltask.git.utils import commit_exists

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="fatal: Not a valid object name"
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = commit_exists("nonexistent")
        assert result is False

    def test_rejects_dash_prefix_commit(self):
        """commit_exists raises ValueError for commit refs starting with dash."""
        from formaltask.git.utils import commit_exists

        with pytest.raises(ValueError, match="commit ref cannot start with '-'"):
            commit_exists("--help")


class TestIsAncestor:
    """Tests for is_ancestor()."""

    def test_returns_true_for_ancestor(self, monkeypatch):
        """is_ancestor returns True when commit is ancestor of target."""
        from formaltask.git.utils import is_ancestor

        # Mock commit_exists to return True
        monkeypatch.setattr("formaltask.git.utils.commit_exists", lambda c, r=None: True)

        # Mock _run_git_command to return success (returncode 0 = is ancestor)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = is_ancestor("abc123", "HEAD")
        assert result is True

    def test_returns_false_for_non_ancestor(self, monkeypatch):
        """is_ancestor returns False when commit is not ancestor of target."""
        from formaltask.git.utils import is_ancestor

        monkeypatch.setattr("formaltask.git.utils.commit_exists", lambda c, r=None: True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = is_ancestor("abc123", "HEAD")
        assert result is False

    def test_returns_none_for_missing_commit(self, monkeypatch):
        """is_ancestor returns None when commit doesn't exist."""
        from formaltask.git.utils import is_ancestor

        monkeypatch.setattr("formaltask.git.utils.commit_exists", lambda c, r=None: False)

        result = is_ancestor("nonexistent", "HEAD")
        assert result is None

    def test_rejects_dash_prefix_commit(self):
        """is_ancestor raises ValueError for commit refs starting with dash."""
        from formaltask.git.utils import is_ancestor

        with pytest.raises(ValueError, match="commit ref cannot start with '-'"):
            is_ancestor("--help", "HEAD")

    def test_rejects_dash_prefix_target(self):
        """is_ancestor raises ValueError for target refs starting with dash."""
        from formaltask.git.utils import is_ancestor

        with pytest.raises(ValueError, match="target ref cannot start with '-'"):
            is_ancestor("abc123", "--version")




class TestFindTaskInCommits:
    """Tests for find_task_in_commits() squash merge fallback."""

    def test_returns_true_when_task_found(self, monkeypatch):
        """find_task_in_commits returns True when task ID in commit message."""
        from formaltask.git.utils import find_task_in_commits

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc123 Task #42 - Fix auth\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_task_in_commits(42)
        assert result is True

    def test_no_false_positive_for_longer_task_id(self, monkeypatch):
        """find_task_in_commits uses negative lookahead to prevent Task #1 matching Task #100.

        The regex 'Task #{task_id}(?![0-9])' ensures Task #1 won't match commits
        containing Task #100, Task #123, etc. This prevents false positives when
        searching for lower task IDs that are prefixes of higher ones.
        """
        from formaltask.git.utils import find_task_in_commits

        # Commit message contains "Task #100", NOT "Task #1"
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc123 Task #100 - Fix auth\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        # Searching for Task #1 should return False (not a false positive)
        result = find_task_in_commits(1)
        assert result is False

    def test_matches_task_with_trailing_non_digit(self, monkeypatch):
        """find_task_in_commits matches 'Task #42:' and 'Task #42-foo' correctly.

        The regex should match task ID followed by non-digit characters like
        colons, hyphens, or spaces - common in commit message formats.
        """
        from formaltask.git.utils import find_task_in_commits

        # Commit message has "Task #42:" with colon suffix (common format)
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc123 Task #42: Fix auth flow\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_task_in_commits(42)
        assert result is True

    def test_returns_false_on_git_timeout(self, monkeypatch):
        """find_task_in_commits returns False when git command times out."""
        from formaltask.git.utils import find_task_in_commits

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = find_task_in_commits(42)
        assert result is False

    def test_returns_false_on_git_fatal_error(self, monkeypatch):
        """find_task_in_commits returns False when git returns non-zero (fatal error)."""
        from formaltask.git.utils import find_task_in_commits

        # Git fatal error (e.g., not a git repository)
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_task_in_commits(42)
        assert result is False

    def test_returns_false_when_no_commits_match(self, monkeypatch):
        """find_task_in_commits returns False when git returns empty output."""
        from formaltask.git.utils import find_task_in_commits

        # Git command succeeds but returns no matching commits
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_task_in_commits(999)
        assert result is False


class TestGetDefaultBranch:
    """Tests for get_default_branch() function."""

    def test_returns_branch_from_symbolic_ref(self, monkeypatch):
        """Returns branch name when symbolic-ref succeeds."""
        from formaltask.git.utils import get_default_branch

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="refs/remotes/origin/main\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_default_branch()
        assert result == "main"

    def test_returns_master_from_symbolic_ref(self, monkeypatch):
        """Returns master when symbolic-ref points to master."""
        from formaltask.git.utils import get_default_branch

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="refs/remotes/origin/master\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_default_branch()
        assert result == "master"

    def test_fallback_to_main_when_symbolic_ref_fails(self, monkeypatch):
        """Falls back to checking origin/main when symbolic-ref fails."""
        from formaltask.git.utils import get_default_branch

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # symbolic-ref fails
                return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
            # rev-parse --verify origin/main succeeds
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_default_branch()
        assert result == "main"

    def test_fallback_to_master_when_no_main(self, monkeypatch):
        """Falls back to master when both symbolic-ref and origin/main fail."""
        from formaltask.git.utils import get_default_branch

        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_default_branch()
        assert result == "master"

    def test_handles_branch_with_slashes(self, monkeypatch):
        """Correctly parses branch names containing slashes (e.g., feature/main)."""
        from formaltask.git.utils import get_default_branch

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="refs/remotes/origin/feature/main\n", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = get_default_branch()
        assert result == "feature/main"

    def test_handles_timeout(self, monkeypatch):
        """Returns master on timeout."""
        from formaltask.git.utils import get_default_branch

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_default_branch()
        assert result == "master"


class TestFetchRemote:
    """Tests for fetch_remote() function."""

    def test_fetch_remote_succeeds(self, monkeypatch):
        """fetch_remote returns True on successful fetch."""
        from formaltask.git.utils import fetch_remote

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = fetch_remote("origin", "master")
        assert result is True

    def test_fetch_remote_returns_false_on_failure(self, monkeypatch):
        """fetch_remote returns False when git fetch fails."""
        from formaltask.git.utils import fetch_remote

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="fatal: could not read from remote"
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = fetch_remote("origin", "master")
        assert result is False

    def test_fetch_remote_returns_false_on_timeout(self, monkeypatch):
        """fetch_remote returns False when git fetch times out."""
        from formaltask.git.utils import fetch_remote

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = fetch_remote("origin", "master")
        assert result is False

    def test_fetch_remote_returns_false_on_network_error(self, monkeypatch):
        """fetch_remote returns False on network errors (graceful degradation)."""
        from formaltask.git.utils import fetch_remote

        def mock_run(*args, **kwargs):
            raise OSError("Network is unreachable")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = fetch_remote("origin", "master")
        assert result is False


class TestFindPrInCommits:
    """Tests for find_pr_in_commits() PR number search."""

    def test_returns_true_when_pr_found(self, monkeypatch):
        """find_pr_in_commits returns True when PR number found in commits."""
        from formaltask.git.utils import find_pr_in_commits

        # Simulate git log output with PR reference
        mock_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="feat: Add new feature (#2126)\n\nImplementation details...",
            stderr="",
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_pr_in_commits(2126)
        assert result is True

    def test_returns_false_when_pr_not_found(self, monkeypatch):
        """find_pr_in_commits returns False when PR number not in commits."""
        from formaltask.git.utils import find_pr_in_commits

        # Simulate empty git log output (no matching commits)
        mock_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        result = find_pr_in_commits(2126)
        assert result is False
