"""Integration tests for formaltask.git.utils with real git repos.

These tests use real subprocess calls to git and were moved from tests/unit/
per Bernhardt boundary audit - integration tests belong in tests/integration/.
"""

import subprocess


class TestGetHeadShaIntegration:
    """Integration tests for get_head_sha() with real git repos."""

    def test_returns_sha_in_real_git_repo(self, git_repo):
        """get_head_sha returns valid 40-char SHA in real git repo."""
        from formaltask.git.utils import get_head_sha

        sha = get_head_sha(git_repo)
        assert sha is not None
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_returns_none_outside_git_repo(self, tmp_path):
        """get_head_sha returns None when not in git repo."""
        from formaltask.git.utils import get_head_sha

        # tmp_path is not a git repo
        sha = get_head_sha(tmp_path)
        assert sha is None


class TestCommitExistsIntegration:
    """Integration tests for commit_exists() with real git repos."""

    def test_returns_true_for_existing_commit_in_real_repo(self, git_repo):
        """commit_exists returns True for HEAD in real git repo."""
        from formaltask.git.utils import commit_exists, get_head_sha

        sha = get_head_sha(git_repo)
        assert sha is not None
        assert commit_exists(sha, git_repo) is True

    def test_returns_false_for_nonexistent_commit_in_real_repo(self, git_repo):
        """commit_exists returns False for nonexistent SHA in real git repo."""
        from formaltask.git.utils import commit_exists

        fake_sha = "0" * 40
        assert commit_exists(fake_sha, git_repo) is False


class TestIsAncestorIntegration:
    """Integration tests for is_ancestor() with real git repos."""

    def test_returns_true_for_ancestor_in_real_repo(self, git_repo):
        """is_ancestor returns True when commit is ancestor in real repo."""
        from formaltask.git.utils import get_head_sha, is_ancestor

        # git_repo has first commit; get its SHA then add second commit
        first_sha = get_head_sha(git_repo)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "second"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # First commit should be ancestor of HEAD
        assert is_ancestor(first_sha, "HEAD", git_repo) is True

    def test_returns_none_for_missing_commit_in_real_repo(self, git_repo):
        """is_ancestor returns None when commit doesn't exist in real repo."""
        from formaltask.git.utils import is_ancestor

        fake_sha = "0" * 40
        assert is_ancestor(fake_sha, "HEAD", git_repo) is None


class TestFindTaskInCommitsIntegration:
    """Integration tests for find_task_in_commits() with real git repos."""

    def test_finds_task_in_real_commit(self, git_repo):
        """find_task_in_commits returns True when task found in real git repo."""
        from formaltask.git.utils import find_task_in_commits

        # Add commit with task reference (git_repo already has init commit)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "feat: Task #42 - Add feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        assert find_task_in_commits(42, repo_path=git_repo) is True
