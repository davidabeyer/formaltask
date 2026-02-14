"""Tests for find_dependency_cycle() function (Task #1885).

Tests the pure function that replaces CircularDependencyChecker class.
TDD Red Phase: Test written before implementation.
"""


def test_find_dependency_cycle_returns_none_for_dag():
    """find_dependency_cycle returns None when no cycle exists."""
    from formaltask.tasks.dependencies import find_dependency_cycle

    # Simple DAG: 1 -> 2 -> 3
    graph = {1: [2], 2: [3], 3: []}

    result = find_dependency_cycle(graph)

    assert result is None


def test_find_dependency_cycle_returns_path_for_cycle():
    """find_dependency_cycle returns cycle path when cycle exists."""
    from formaltask.tasks.dependencies import find_dependency_cycle

    # Cycle: 1 -> 2 -> 3 -> 1
    graph = {1: [2], 2: [3], 3: [1]}

    result = find_dependency_cycle(graph)

    assert result is not None
    assert len(result) >= 2  # At least 2 nodes in a cycle


def test_find_dependency_cycle_detects_self_loop():
    """find_dependency_cycle detects when node depends on itself."""
    from formaltask.tasks.dependencies import find_dependency_cycle

    # Self-loop: task 1 depends on itself
    graph = {1: [1]}

    result = find_dependency_cycle(graph)

    assert result is not None, "Should detect self-loop as a cycle"
    assert 1 in result, "Cycle should contain the self-referencing node"


def test_find_dependency_cycle_returns_none_for_empty_graph():
    """find_dependency_cycle returns None for empty graph."""
    from formaltask.tasks.dependencies import find_dependency_cycle

    # Empty graph (no tasks)
    graph = {}

    result = find_dependency_cycle(graph)

    assert result is None, "Empty graph should have no cycles"


def test_find_dependency_cycle_detects_mid_chain_cycle():
    """find_dependency_cycle detects cycle that starts mid-chain."""
    from formaltask.tasks.dependencies import find_dependency_cycle

    # Complex graph: 1 -> 2 -> 3 -> 4 -> 2 (cycle starts at 2)
    # Task 1 is outside the cycle
    graph = {1: [2], 2: [3], 3: [4], 4: [2]}

    result = find_dependency_cycle(graph)

    assert result is not None, "Should detect cycle even when entry point is outside cycle"
    # Cycle should contain 2, 3, and 4
    assert 2 in result, "Cycle should contain node 2"
    assert 3 in result, "Cycle should contain node 3"
    assert 4 in result, "Cycle should contain node 4"
