# Cadence Check

Query SQLite for last invocation, compare to target intervals:

```python
import sys
from pathlib import Path

# Add your life/tracking database root
# sys.path.insert(0, str(Path.home() / "life"))
# from db.invocation import get_cadence

TARGETS = {
    # "skill:mode": ("skill", "mode", target_days),
    # Example:
    # "plan:plan-today": ("plan", "plan-today", 1),
}

due = []
for key, (skill, mode, target_days) in TARGETS.items():
    cadence = get_cadence(skill, mode)
    if cadence["days_ago"] is None or cadence["days_ago"] > target_days:
        days = f"{cadence['days_ago']:.0f}" if cadence["days_ago"] else "never"
        due.append(f"DUE: {key} (target: every {target_days}d, last: {days}d ago)")

if due:
    for item in due:
        print(item)
else:
    print("All cadences on track.")
```

Show DUE items to user. Don't nag — just surface.
