#!/bin/bash
# Delete verified merged task worktrees and branches

set -e

echo "=================================================="
echo "CLEANING UP VERIFIED MERGED TASKS"
echo "=================================================="
echo ""

# Tasks that are verified merged (all 7)
MERGED_TASKS=(926 927 928 929 952 960 968)

for task_num in "${MERGED_TASKS[@]}"; do
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
echo "REMAINING OPEN TASKS (NOT MERGED)"
echo "=================================================="
echo ""

# Find remaining task worktrees
remaining=$(find $HOME -maxdepth 1 -type d -name "task-*" 2>/dev/null | wc -l)

if [ "$remaining" -gt 0 ]; then
    echo "Open task worktrees remaining:"
    find $HOME -maxdepth 1 -type d -name "task-*" 2>/dev/null | while read dir; do
        task_name=$(basename "$dir")
        task_num=$(echo "$task_name" | grep -oE '[0-9]+' | head -1)
        echo "  • Task #$task_num - $task_name"
    done
else
    echo "No task worktrees remaining!"
fi

echo ""
echo "=================================================="
echo "CLEANUP COMPLETE"
echo "=================================================="
