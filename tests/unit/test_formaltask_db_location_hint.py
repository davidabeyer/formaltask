"""Tests for SessionStart hook: formaltask_db_location_hint.py"""


def test_get_main_repo_db_path_returns_none_when_no_task_dir(tmp_path):
    """Should return None when .task/ directory doesn't exist."""
    from hooks.session_start.formaltask_db_location_hint import get_main_repo_db_path

    result = get_main_repo_db_path(tmp_path)
    assert result is None


def test_get_main_repo_db_path_returns_path_from_main_repo_file(tmp_path):
    """Should read main_repo file and return db path if db exists."""
    from hooks.session_start.formaltask_db_location_hint import get_main_repo_db_path

    # Setup worktree with .task/main_repo
    task_dir = tmp_path / ".task"
    task_dir.mkdir()

    # Setup main repo with db
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    db_dir = main_repo / ".claude"
    db_dir.mkdir()
    db_file = db_dir / "formaltask.db"
    db_file.touch()

    (task_dir / "main_repo").write_text(str(main_repo))

    result = get_main_repo_db_path(tmp_path)
    assert result == str(db_file)


def test_main_outputs_warning_when_local_db_could_confuse(tmp_path, monkeypatch, capsys):
    """Should output warning JSON when local db exists alongside main repo db.

    Warning should include db path and CLI usage examples.
    """
    import json

    from hooks.session_start.formaltask_db_location_hint import main

    # Setup worktree structure
    task_dir = tmp_path / ".task"
    task_dir.mkdir()
    (task_dir / "id").write_text("1213")

    # Main repo with db
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    main_db_dir = main_repo / ".claude"
    main_db_dir.mkdir()
    main_db = main_db_dir / "formaltask.db"
    main_db.touch()
    (task_dir / "main_repo").write_text(str(main_repo))

    # Local db (stale copy that could confuse)
    local_db_dir = tmp_path / ".claude"
    local_db_dir.mkdir()
    (local_db_dir / "formaltask.db").touch()

    # Mock cwd to tmp_path
    monkeypatch.chdir(tmp_path)

    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    warning = output["hookSpecificOutput"]["additionalContext"]
    assert "formaltask_database_warning" in warning
    # Should contain db path
    assert str(main_db) in warning
    # Should contain usage example
    assert "--db-path" in warning


def test_get_main_repo_db_path_returns_path_from_project_root_file(tmp_path):
    """Should also check project_root file (alternative to main_repo)."""
    from hooks.session_start.formaltask_db_location_hint import get_main_repo_db_path

    # Setup worktree with .task/project_root (alternative naming)
    task_dir = tmp_path / ".task"
    task_dir.mkdir()

    # Setup main repo with db
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    db_dir = main_repo / ".claude"
    db_dir.mkdir()
    db_file = db_dir / "formaltask.db"
    db_file.touch()

    # Use project_root instead of main_repo
    (task_dir / "project_root").write_text(str(main_repo))

    result = get_main_repo_db_path(tmp_path)
    assert result == str(db_file)


def test_warns_about_home_claude_db_misconception(tmp_path, monkeypatch, capsys):
    """Should warn when in worktree that ~/.claude/formaltask.db is wrong location."""
    import json

    from hooks.session_start import formaltask_db_location_hint

    # Simulate being in a worktree under ~/.claude/worktrees/
    # The key insight: worktrees are at ~/.claude/worktrees/task-N
    # but the DB is at ~/formaltask/.claude/formaltask.db
    worktree = tmp_path / ".claude" / "worktrees" / "task-42"
    worktree.mkdir(parents=True)

    # Setup .task with main_repo pointing to formaltask location
    task_dir = worktree / ".task"
    task_dir.mkdir()
    (task_dir / "id").write_text("42")

    # Main repo is at a different location (simulating ~/formaltask)
    main_repo = tmp_path / "formaltask"
    main_repo.mkdir()
    main_db_dir = main_repo / ".claude"
    main_db_dir.mkdir()
    main_db = main_db_dir / "formaltask.db"
    main_db.touch()
    (task_dir / "main_repo").write_text(str(main_repo))

    # The WRONG db at ~/.claude/formaltask.db (common misconception)
    wrong_db = tmp_path / ".claude" / "formaltask.db"
    wrong_db.touch()

    # Mock get_home_claude_db_path to return our test path
    monkeypatch.setattr(
        formaltask_db_location_hint,
        "get_home_claude_db_path",
        lambda: wrong_db,
    )

    monkeypatch.chdir(worktree)
    formaltask_db_location_hint.main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    warning = output["hookSpecificOutput"]["additionalContext"]

    # Should warn about the correct db path
    assert str(main_db) in warning
    # Should mention ~/.claude/formaltask.db is wrong
    assert "~/.claude/formaltask.db" in warning or "NOT" in warning
