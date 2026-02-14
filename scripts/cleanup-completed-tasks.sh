#!/bin/bash
# Delete completed task worktrees and branches

set -e

echo "=================================================="
echo "CLEANING UP COMPLETED TASKS"
echo "=================================================="
echo ""

# Completed tasks that still have worktrees
COMPLETED_TASKS=(931 966 971)

for task_num in "${COMPLETED_TASKS[@]}"; do
    # Find worktree with this task number
    task_dir=$(find $HOME -maxdepth 1 -type d -name "task-${task_num}-*" 2>/dev/null | head -1)

    if [ -z "$task_dir" ]; then
        echo "Task #$task_num: Not found (already deleted)"
        continue
    fi

    task_name=$(basename "$task_dir")
    echo "Task #$task_num ($task_name):"

    # Remove worktree
    if [ -d "$task_dir" ]; then
        git worktree remove "$task_dir" --force 2>/dev/null || true
        echo "  ✓ Worktree removed"
    fi

    # Delete local branch
    git branch -D "$task_name" 2>/dev/null || true
    echo "  ✓ Local branch deleted"
    echo ""
done

echo "=================================================="
echo "REMAINING IN-PROGRESS TASKS"
echo "=================================================="
echo ""
echo "In-progress tasks with active worktrees:"
echo "  • Task #906 - Cleanup and Documentation"
echo "  • Task #955 - Create Migration for Worker Columns"
echo "  • Task #969 - Fix Broken Command References"
echo "  • Task #975 - Add --depends-on flag to pm task-add"
echo ""
echo "=================================================="
echo "CLEANUP COMPLETE"
echo "=================================================="
