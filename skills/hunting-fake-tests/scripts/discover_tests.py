#!/usr/bin/env python3
"""
Discover and categorize all tests in the codebase.
Outputs a JSON manifest for partition planning.
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TestFile:
    path: str
    framework: str  # pytest, bats
    test_count: int
    line_count: int
    module: str  # logical grouping


def count_pytest_tests(filepath: Path) -> int:
    """Count test functions/methods in a pytest file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    # Match: def test_*, async def test_*, class Test*
    test_funcs = len(re.findall(r"^\s*(?:async\s+)?def\s+test_\w+", content, re.MULTILINE))
    test_classes = len(re.findall(r"^\s*class\s+Test\w+", content, re.MULTILINE))
    return test_funcs + test_classes


def count_bats_tests(filepath: Path) -> int:
    """Count @test blocks in a BATS file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^@test\s+", content, re.MULTILINE))


def get_module(filepath: Path, root: Path) -> str:
    """Extract logical module from file path."""
    rel = filepath.relative_to(root)
    parts = rel.parts[:-1]  # exclude filename
    if not parts:
        return "root"
    # Return first 2 levels max for grouping
    return "/".join(parts[:2])


def discover_tests(root: Optional[Path] = None) -> dict:
    """Discover all test files and return manifest."""
    root = root or Path.cwd()

    # Skip common non-test directories
    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".tox",
        "site-packages",
        ".claude",
    }

    test_files: list[TestFile] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip directories
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        dir_path = Path(dirpath)

        for fname in filenames:
            filepath = dir_path / fname

            # Pytest files
            if fname.startswith("test_") and fname.endswith(".py"):
                test_files.append(
                    TestFile(
                        path=str(filepath.relative_to(root)),
                        framework="pytest",
                        test_count=count_pytest_tests(filepath),
                        line_count=len(
                            filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
                        ),
                        module=get_module(filepath, root),
                    )
                )
            elif fname.endswith("_test.py"):
                test_files.append(
                    TestFile(
                        path=str(filepath.relative_to(root)),
                        framework="pytest",
                        test_count=count_pytest_tests(filepath),
                        line_count=len(
                            filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
                        ),
                        module=get_module(filepath, root),
                    )
                )
            elif fname == "conftest.py":
                # Track conftest files for fixture awareness
                test_files.append(
                    TestFile(
                        path=str(filepath.relative_to(root)),
                        framework="pytest-fixture",
                        test_count=0,
                        line_count=len(
                            filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
                        ),
                        module=get_module(filepath, root),
                    )
                )
            # BATS files
            elif fname.endswith(".bats"):
                test_files.append(
                    TestFile(
                        path=str(filepath.relative_to(root)),
                        framework="bats",
                        test_count=count_bats_tests(filepath),
                        line_count=len(
                            filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
                        ),
                        module=get_module(filepath, root),
                    )
                )

    # Group by module for partition planning
    modules: dict[str, list[dict]] = defaultdict(list)
    for tf in test_files:
        modules[tf.module].append(asdict(tf))

    # Calculate stats
    total_tests = sum(tf.test_count for tf in test_files)
    total_files = len([tf for tf in test_files if tf.framework != "pytest-fixture"])
    total_lines = sum(tf.line_count for tf in test_files)

    manifest = {
        "summary": {
            "total_test_files": total_files,
            "total_tests": total_tests,
            "total_lines": total_lines,
            "module_count": len(modules),
            "frameworks": {
                "pytest": len([tf for tf in test_files if tf.framework == "pytest"]),
                "bats": len([tf for tf in test_files if tf.framework == "bats"]),
                "conftest": len([tf for tf in test_files if tf.framework == "pytest-fixture"]),
            },
        },
        "modules": dict(modules),
        "large_files": [
            asdict(tf)
            for tf in test_files
            if tf.line_count > 300 and tf.framework != "pytest-fixture"
        ],
        "suggested_batches": suggest_batches(modules, total_tests),
    }

    return manifest


def suggest_batches(modules: dict, total_tests: int) -> list[dict]:
    """Suggest batch partitioning strategy."""
    batches = []
    module_list = sorted(modules.items(), key=lambda x: -sum(f["test_count"] for f in x[1]))

    if len(module_list) <= 10:
        # One batch per module
        for i, (module, files) in enumerate(module_list, 1):
            test_count = sum(f["test_count"] for f in files)
            if test_count > 0:  # Skip fixture-only modules
                batches.append(
                    {
                        "batch_id": i,
                        "module": module,
                        "files": [f["path"] for f in files if f["framework"] != "pytest-fixture"],
                        "test_count": test_count,
                    }
                )
    else:
        # Group into 10 batches
        target_per_batch = total_tests // 10
        current_batch = {"batch_id": 1, "modules": [], "files": [], "test_count": 0}

        for module, files in module_list:
            test_count = sum(f["test_count"] for f in files)
            if test_count == 0:
                continue

            current_batch["modules"].append(module)
            current_batch["files"].extend(
                [f["path"] for f in files if f["framework"] != "pytest-fixture"]
            )
            current_batch["test_count"] += test_count

            if current_batch["test_count"] >= target_per_batch and len(batches) < 9:
                batches.append(current_batch)
                current_batch = {
                    "batch_id": len(batches) + 1,
                    "modules": [],
                    "files": [],
                    "test_count": 0,
                }

        if current_batch["files"]:
            batches.append(current_batch)

    return batches


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    manifest = discover_tests(root)
    print(json.dumps(manifest, indent=2))
