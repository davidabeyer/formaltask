"""Tests for render_template_file() in formaltask/core/rules.py."""

import logging

import pytest


@pytest.fixture()
def bundled_dir(tmp_path):
    """Create a bundled templates directory with a test template."""
    d = tmp_path / "bundled"
    d.mkdir()
    (d / "greeting.md.j2").write_text("Hello from bundled, {{ name }}!")
    return d


@pytest.fixture()
def user_dir(tmp_path):
    """Create a user overlay templates directory."""
    d = tmp_path / "user"
    d.mkdir()
    return d


def test_user_overlay_precedence(bundled_dir, user_dir):
    """User overlay template takes precedence over bundled."""
    from formaltask.core.rules import render_template_file

    (user_dir / "greeting.md.j2").write_text("Hello from USER, {{ name }}!")

    result = render_template_file(
        "greeting.md.j2",
        {"name": "World"},
        search_paths=[str(user_dir), str(bundled_dir)],
    )
    assert result == "Hello from USER, World!"


def test_falls_back_to_bundled(bundled_dir, user_dir):
    """Falls back to bundled when user overlay doesn't have the template."""
    from formaltask.core.rules import render_template_file

    result = render_template_file(
        "greeting.md.j2",
        {"name": "World"},
        search_paths=[str(user_dir), str(bundled_dir)],
    )
    assert result == "Hello from bundled, World!"


def test_logs_user_overlay(bundled_dir, user_dir, caplog):
    """DEBUG log emitted when user template is used."""
    from formaltask.core.rules import render_template_file

    (user_dir / "greeting.md.j2").write_text("Hello from USER, {{ name }}!")

    with caplog.at_level(logging.DEBUG, logger="formaltask.core.rules"):
        render_template_file(
            "greeting.md.j2",
            {"name": "World"},
            search_paths=[str(user_dir), str(bundled_dir)],
        )

    assert any("Using user template" in msg for msg in caplog.messages)


def test_falls_back_on_user_template_parse_error(bundled_dir, user_dir, caplog):
    """Falls back to bundled when user template has a syntax error."""
    from formaltask.core.rules import render_template_file

    (user_dir / "greeting.md.j2").write_text("{% if unclosed")

    with caplog.at_level(logging.WARNING, logger="formaltask.core.rules"):
        result = render_template_file(
            "greeting.md.j2",
            {"name": "World"},
            search_paths=[str(user_dir), str(bundled_dir)],
        )

    assert result == "Hello from bundled, World!"
    assert any("parse error" in msg.lower() or "syntax" in msg.lower() for msg in caplog.messages)


def test_include_resolves_from_search_path(bundled_dir, user_dir):
    """{% include %} resolves templates from the search path."""
    from formaltask.core.rules import render_template_file

    (bundled_dir / "header.md.j2").write_text("# Header for {{ title }}")
    (bundled_dir / "page.md.j2").write_text(
        '{% include "header.md.j2" %}\n\nBody content.'
    )

    result = render_template_file(
        "page.md.j2",
        {"title": "My Page"},
        search_paths=[str(user_dir), str(bundled_dir)],
    )
    assert result == "# Header for My Page\n\nBody content."
