"""Tests for compaction breadcrumb carry-forward.

Two pieces:
1. PreCompact hook writes carry-forward file with old session_id
2. SessionStart phase adopts orphaned breadcrumbs with new session_id
"""

import json
from datetime import UTC, datetime, timedelta


class TestPreCompactCarryForward:
    """PreCompact hook writes compacting-session.json."""

    def test_writes_carry_forward_file(self, tmp_path):
        """PreCompact writes old session_id to carry-forward file."""
        from hooks.pre_compact.carry_forward import carry_forward_breadcrumbs

        carry_file = tmp_path / "compacting-session.json"
        ctx = {"session_id": "old-session-abc"}

        carry_forward_breadcrumbs(ctx, carry_file=carry_file)

        data = json.loads(carry_file.read_text())
        assert data["old_session_id"] == "old-session-abc"
        assert "timestamp" in data

    def test_no_session_id_does_nothing(self, tmp_path):
        """No session_id in payload → no file written."""
        from hooks.pre_compact.carry_forward import carry_forward_breadcrumbs

        carry_file = tmp_path / "compacting-session.json"
        ctx = {}

        carry_forward_breadcrumbs(ctx, carry_file=carry_file)

        assert not carry_file.exists()

    def test_overwrites_existing_carry_forward(self, tmp_path):
        """Subsequent compaction overwrites previous carry-forward."""
        from hooks.pre_compact.carry_forward import carry_forward_breadcrumbs

        carry_file = tmp_path / "compacting-session.json"
        carry_file.write_text(json.dumps({"old_session_id": "stale"}))

        carry_forward_breadcrumbs({"session_id": "fresh"}, carry_file=carry_file)

        data = json.loads(carry_file.read_text())
        assert data["old_session_id"] == "fresh"


class TestSessionStartAdoptBreadcrumbs:
    """SessionStart adopts orphaned breadcrumbs from compacted session."""

    def test_retags_breadcrumbs_with_new_session_id(self, tmp_path):
        """Breadcrumbs from old session get new session_id."""
        from hooks.session_start.phases import run_adopt_compacted_breadcrumbs

        breadcrumbs_file = tmp_path / "active-skills.json"
        carry_file = tmp_path / "compacting-session.json"

        breadcrumbs_file.write_text(
            json.dumps(
                [
                    {
                        "skill": "critiquing",
                        "session_id": "old-abc",
                        "run_dir": "/tmp/run1",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    {
                        "skill": "planning",
                        "session_id": "other-session",
                        "run_dir": "/tmp/run2",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                ]
            )
        )
        carry_file.write_text(
            json.dumps(
                {
                    "old_session_id": "old-abc",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        )

        ctx = {"session_id": "new-xyz"}
        run_adopt_compacted_breadcrumbs(
            ctx, breadcrumbs_file=breadcrumbs_file, carry_file=carry_file
        )

        result = json.loads(breadcrumbs_file.read_text())
        assert result[0]["session_id"] == "new-xyz"  # Re-tagged
        assert result[1]["session_id"] == "other-session"  # Untouched
        assert not carry_file.exists()  # Cleaned up

    def test_no_carry_forward_file_is_noop(self, tmp_path):
        """No carry-forward file → nothing happens."""
        from hooks.session_start.phases import run_adopt_compacted_breadcrumbs

        breadcrumbs_file = tmp_path / "active-skills.json"
        carry_file = tmp_path / "compacting-session.json"

        breadcrumbs_file.write_text(
            json.dumps(
                [
                    {
                        "skill": "x",
                        "session_id": "abc",
                        "run_dir": "/tmp/r",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                ]
            )
        )

        ctx = {"session_id": "new-xyz"}
        run_adopt_compacted_breadcrumbs(
            ctx, breadcrumbs_file=breadcrumbs_file, carry_file=carry_file
        )

        result = json.loads(breadcrumbs_file.read_text())
        assert result[0]["session_id"] == "abc"  # Unchanged

    def test_stale_carry_forward_ignored(self, tmp_path):
        """Carry-forward older than 2 minutes is ignored."""
        from hooks.session_start.phases import run_adopt_compacted_breadcrumbs

        breadcrumbs_file = tmp_path / "active-skills.json"
        carry_file = tmp_path / "compacting-session.json"

        breadcrumbs_file.write_text(
            json.dumps(
                [
                    {
                        "skill": "x",
                        "session_id": "old-abc",
                        "run_dir": "/tmp/r",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                ]
            )
        )
        stale_time = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        carry_file.write_text(
            json.dumps(
                {
                    "old_session_id": "old-abc",
                    "timestamp": stale_time,
                }
            )
        )

        ctx = {"session_id": "new-xyz"}
        run_adopt_compacted_breadcrumbs(
            ctx, breadcrumbs_file=breadcrumbs_file, carry_file=carry_file
        )

        result = json.loads(breadcrumbs_file.read_text())
        assert result[0]["session_id"] == "old-abc"  # NOT re-tagged
        assert not carry_file.exists()  # Still cleaned up

    def test_no_breadcrumbs_file_is_noop(self, tmp_path):
        """No active-skills.json → nothing happens."""
        from hooks.session_start.phases import run_adopt_compacted_breadcrumbs

        breadcrumbs_file = tmp_path / "active-skills.json"
        carry_file = tmp_path / "compacting-session.json"
        carry_file.write_text(
            json.dumps(
                {
                    "old_session_id": "old-abc",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        )

        ctx = {"session_id": "new-xyz"}
        run_adopt_compacted_breadcrumbs(
            ctx, breadcrumbs_file=breadcrumbs_file, carry_file=carry_file
        )

        assert not carry_file.exists()  # Cleaned up even without breadcrumbs

    def test_no_new_session_id_is_noop(self, tmp_path):
        """No session_id in ctx → can't re-tag, skip."""
        from hooks.session_start.phases import run_adopt_compacted_breadcrumbs

        breadcrumbs_file = tmp_path / "active-skills.json"
        carry_file = tmp_path / "compacting-session.json"

        breadcrumbs_file.write_text(
            json.dumps(
                [
                    {
                        "skill": "x",
                        "session_id": "old-abc",
                        "run_dir": "/tmp/r",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                ]
            )
        )
        carry_file.write_text(
            json.dumps(
                {
                    "old_session_id": "old-abc",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        )

        ctx = {}
        run_adopt_compacted_breadcrumbs(
            ctx, breadcrumbs_file=breadcrumbs_file, carry_file=carry_file
        )

        result = json.loads(breadcrumbs_file.read_text())
        assert result[0]["session_id"] == "old-abc"  # Unchanged
