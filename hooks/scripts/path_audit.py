"""Path pattern audit for test reorganization.

Scans codebase for Path(__file__) patterns and generates audit report.
Task #2124: Pre-flight Checks and Path Pattern Audit
"""

from pathlib import Path


def scan_for_path_file_patterns(root_path: Path) -> list[dict]:
    """Scan directory for Path(__file__) patterns in Python files.

    Args:
        root_path: Root directory to scan.

    Returns:
        List of file info dicts with path and instances.
    """
    import re

    pattern = re.compile(r"Path\(__file__\)")
    results = []

    for py_file in root_path.rglob("*.py"):
        instances = []
        try:
            with open(py_file, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if pattern.search(line):
                        instances.append(
                            {
                                "line": line_num,
                                "pattern": "Path(__file__)",
                                "context": line.strip(),
                            }
                        )
        except (OSError, UnicodeDecodeError):
            # Skip files with read errors or encoding issues
            continue

        if instances:
            rel_path = py_file.relative_to(root_path)
            results.append(
                {
                    "path": str(rel_path),
                    "instances": instances,
                }
            )

    return results


def generate_audit_json(files: list[dict]) -> dict:
    """Generate audit JSON conforming to schema v1.0."""
    from datetime import UTC, datetime

    total_instances = sum(len(f["instances"]) for f in files)

    return {
        "schema_version": "1.0",
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "files": files,
        "summary": {
            "total_files": len(files),
            "total_instances": total_instances,
        },
    }


def generate_baseline_txt(root_path: Path) -> str:
    """Generate baseline.txt content with sorted test file paths."""
    test_files = []

    for py_file in root_path.rglob("test_*.py"):
        rel_path = py_file.relative_to(root_path)
        test_files.append(str(rel_path))

    for py_file in root_path.rglob("conftest.py"):
        rel_path = py_file.relative_to(root_path)
        test_files.append(str(rel_path))

    test_files.sort()
    return "\n".join(test_files)


def main(project_root: Path, output_json_path: Path, output_baseline_path: Path) -> None:
    """Execute path audit and generate output files."""
    import json

    files = scan_for_path_file_patterns(project_root)
    audit_data = generate_audit_json(files)

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    baseline = generate_baseline_txt(project_root)
    output_baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_baseline_path, "w", encoding="utf-8") as f:
        f.write(baseline)
