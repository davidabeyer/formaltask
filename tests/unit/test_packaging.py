from pathlib import Path
import plistlib


def test_ft_watch_launch_agent_points_at_checkout_bootstrap() -> None:
    repo = Path(__file__).resolve().parents[2]
    bootstrap = repo / "scripts" / "ft-watch-bootstrap.sh"
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.ft.watch.plist"

    plist = plistlib.loads(plist_path.read_bytes())

    assert plist["ProgramArguments"] == [str(bootstrap)]
    assert bootstrap.exists()
    assert bootstrap.stat().st_mode & 0o111
