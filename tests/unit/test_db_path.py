"""Tests for get_db_path() - centralized database path resolution."""

import contextlib
from unittest.mock import patch

import pytest


class TestGetDbPath:
    """Tests for get_db_path() function."""

    def test_returns_project_root_db_when_env_set(self, tmp_path, monkeypatch):
        """Should use PROJECT_ROOT/.claude/formaltask.db when env is set."""
        from formaltask.db.path import get_db_path

        # Setup: create db at PROJECT_ROOT
        db_dir = tmp_path / ".claude"
        db_dir.mkdir()
        db_file = db_dir / "formaltask.db"
        db_file.touch()

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

        result = get_db_path()

        assert result == db_file

    def test_worktree_finds_main_repo_db(self, tmp_path, monkeypatch):
        """Should find main repo db when in a worktree with .task/main_repo."""
        from formaltask.db.path import get_db_path

        # Setup main repo with db
        main_repo = tmp_path / "main_repo"
        main_claude = main_repo / ".claude"
        main_claude.mkdir(parents=True)
        main_db = main_claude / "formaltask.db"
        main_db.touch()

        # Setup worktree with .task/main_repo pointer
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        task_dir = worktree / ".task"
        task_dir.mkdir()
        (task_dir / "main_repo").write_text(str(main_repo))

        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        monkeypatch.chdir(worktree)

        result = get_db_path()

        assert result == main_db

    def test_rejects_symlinked_db_file(self, tmp_path, monkeypatch):
        """Should reject symlinked database file for security."""
        from formaltask.db.path import get_db_path

        # Setup: create real db elsewhere, symlink in .claude
        real_db = tmp_path / "real.db"
        real_db.touch()

        db_dir = tmp_path / ".claude"
        db_dir.mkdir()
        db_link = db_dir / "formaltask.db"
        db_link.symlink_to(real_db)

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

        with pytest.raises(ValueError, match="Symlink not allowed"):
            get_db_path()

    def test_rejects_symlinked_claude_dir(self, tmp_path, monkeypatch):
        """Should reject symlinked .claude directory for security."""
        from formaltask.db.path import get_db_path

        # Setup: real .claude elsewhere, symlink in project
        real_claude = tmp_path / "real_claude"
        real_claude.mkdir()
        (real_claude / "formaltask.db").touch()

        project = tmp_path / "project"
        project.mkdir()
        claude_link = project / ".claude"
        claude_link.symlink_to(real_claude)

        monkeypatch.setenv("PROJECT_ROOT", str(project))

        with pytest.raises(ValueError, match="Symlink not allowed"):
            get_db_path()

    def test_worktree_rejects_symlinked_main_repo(self, tmp_path, monkeypatch):
        """Should reject worktree pointer to symlinked main repo directory."""
        from formaltask.db.path import get_db_path

        # Setup: real main repo
        real_main = tmp_path / "real_main"
        (real_main / ".claude").mkdir(parents=True)
        (real_main / ".claude" / "formaltask.db").touch()

        # Setup: symlink to main repo
        symlinked_main = tmp_path / "symlinked_main"
        symlinked_main.symlink_to(real_main)

        # Setup: worktree pointing to symlinked main
        worktree = tmp_path / "worktree"
        (worktree / ".claude").mkdir(parents=True)
        (worktree / ".claude" / "formaltask.db").touch()
        (worktree / ".task").mkdir()
        (worktree / ".task" / "main_repo").write_text(str(symlinked_main))

        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        monkeypatch.chdir(worktree)

        # Should fall back to cwd (worktree) db, not follow symlinked main_repo
        result = get_db_path()
        assert result == worktree / ".claude" / "formaltask.db"

    def test_cwd_fallback_when_no_env_no_worktree(self, tmp_path, monkeypatch):
        """Should use cwd/.claude/formaltask.db as fallback."""
        from formaltask.db.path import get_db_path

        db_dir = tmp_path / ".claude"
        db_dir.mkdir()
        (db_dir / "formaltask.db").touch()

        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = get_db_path()
        assert result == db_dir / "formaltask.db"

    def test_raises_file_not_found_when_db_missing(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError when database doesn't exist."""
        from formaltask.db.path import get_db_path

        db_dir = tmp_path / ".claude"
        db_dir.mkdir()
        # Note: NOT creating formaltask.db

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

        with pytest.raises(FileNotFoundError, match="formaltask.db not found"):
            get_db_path()

    def test_worktree_uses_project_root_pointer(self, tmp_path, monkeypatch):
        """Should find db via .task/project_root (alternative to main_repo)."""
        from formaltask.db.path import get_db_path

        # Setup main repo with db
        main_repo = tmp_path / "main"
        (main_repo / ".claude").mkdir(parents=True)
        (main_repo / ".claude" / "formaltask.db").touch()

        # Setup worktree with project_root (not main_repo)
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".task").mkdir()
        (worktree / ".task" / "project_root").write_text(str(main_repo))

        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        monkeypatch.chdir(worktree)

        result = get_db_path()
        assert result == main_repo / ".claude" / "formaltask.db"

    def test_logs_debug_on_oserror_reading_pointer(self, tmp_path, monkeypatch, caplog):
        """Should log debug message when OSError reading pointer file."""
        import logging

        from formaltask.db.path import get_db_path

        # Setup worktree with unreadable pointer file
        worktree = tmp_path / "worktree"
        (worktree / ".claude").mkdir(parents=True)
        (worktree / ".claude" / "formaltask.db").touch()
        (worktree / ".task").mkdir()
        pointer = worktree / ".task" / "main_repo"
        pointer.write_text("some content")
        pointer.chmod(0o000)  # Make unreadable

        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        monkeypatch.chdir(worktree)

        with caplog.at_level(logging.DEBUG):
            result = get_db_path()

        # Should fall back to cwd and log the error
        assert result == worktree / ".claude" / "formaltask.db"
        assert "Failed to read" in caplog.text

        # Cleanup: restore permissions for tmp_path cleanup
        pointer.chmod(0o644)

    def test_rejects_home_directory_database(self, tmp_path, monkeypatch):
        """Should reject ~/.claude/formaltask.db as wrong location for project work."""
        from formaltask.db.path import get_db_path

        # Create a fake home directory with a db
        fake_home = tmp_path / "fake_home"
        (fake_home / ".claude").mkdir(parents=True)
        (fake_home / ".claude" / "formaltask.db").touch()

        # Mock Path.home() to return our fake home
        with patch("formaltask.db.path.Path.home", return_value=fake_home):
            monkeypatch.delenv("PROJECT_ROOT", raising=False)
            monkeypatch.chdir(fake_home)

            with pytest.raises(ValueError, match="Refusing to use home directory database"):
                get_db_path()


class TestPmDbPathResolution:
    """Tests for pm.py db_path argument resolution."""

    def test_pm_help_runs_without_error(self):
        """pm --help should run without error."""
        with patch("sys.argv", ["pm", "epic", "list", "--help"]):
            from formaltask.cli import pm

            with contextlib.suppress(SystemExit):
                pm.main()
            # Test passes if no exception raised


class TestValidateUserDbPath:
    """Tests for validate_user_db_path() - user-provided --db-path validation (Task #1965)."""

    def test_accepts_valid_db_file(self, tmp_path):
        """Valid .db file is accepted and returned as Path."""
        from formaltask.db.path import validate_user_db_path

        db_file = tmp_path / "test.db"
        db_file.touch()

        result = validate_user_db_path(str(db_file))

        assert result == db_file

    def test_rejects_symlink(self, tmp_path):
        """Symlink paths are rejected."""
        from formaltask.db.path import validate_user_db_path

        real_file = tmp_path / "real.db"
        real_file.touch()
        symlink = tmp_path / "link.db"
        symlink.symlink_to(real_file)

        with pytest.raises(ValueError, match="symlink"):
            validate_user_db_path(str(symlink))

    def test_requires_db_extension(self, tmp_path):
        """Non-.db files are rejected."""
        from formaltask.db.path import validate_user_db_path

        txt_file = tmp_path / "data.txt"
        txt_file.touch()

        with pytest.raises(ValueError, match="extension"):
            validate_user_db_path(str(txt_file))

    def test_blocks_system_directories(self):
        """System directories (/dev, /proc, /sys, /etc, /var, /boot, /root) are blocked."""
        from formaltask.db.path import validate_user_db_path

        system_paths = [
            "/dev/null.db",
            "/proc/something.db",
            "/sys/device.db",
            "/etc/passwd.db",
            "/var/log/test.db",
            "/boot/grub.db",
            "/root/secret.db",
        ]

        for path in system_paths:
            with pytest.raises(ValueError, match="system directory"):
                validate_user_db_path(path)

    def test_rejects_nonexistent(self, tmp_path):
        """Non-existent paths are rejected."""
        from formaltask.db.path import validate_user_db_path

        nonexistent = tmp_path / "nonexistent.db"

        with pytest.raises(ValueError, match="does not exist"):
            validate_user_db_path(str(nonexistent))

    def test_accepts_uppercase_db_extension(self, tmp_path):
        """Uppercase .DB extension is accepted (case-insensitive)."""
        from formaltask.db.path import validate_user_db_path

        db_file = tmp_path / "test.DB"
        db_file.touch()

        result = validate_user_db_path(str(db_file))

        assert result == db_file
