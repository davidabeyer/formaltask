"""pm blocked command - Mark worker as blocked with a question.

Worker runs this to signal it needs human input to continue.
Shows up in /inbox for human to resolve.
"""

import logging
import sys

from formaltask.cli.exit_codes import ExitCode
from formaltask.db.path import get_db_path
from formaltask.workers.context import get_task_id_from_session

logger = logging.getLogger(__name__)


def setup_parser(subparser):
    """Set up argument parser for blocked command."""
    subparser.add_argument(
        "question",
        help="Question or context for why you're blocked",
    )
    subparser.add_argument(
        "--db-path",
        help="Database path (default: auto-detect)",
    )


def execute(args) -> int:
    """Execute the blocked command."""
    from formaltask.db.connection import DatabaseConnection

    db_path = getattr(args, "db_path", None) or get_db_path()
    question = args.question

    # Get task ID from environment
    task_id = get_task_id_from_session()
    if task_id is None:
        print("No task context. Run from a worker session.", file=sys.stderr)
        return ExitCode.NOT_FOUND.value

    # Note: Subagent restriction is enforced via PreToolUse hooks in agent
    # frontmatter (formaltask/validators/subagent_ft_guard.py), not here.
    # The TMUX check was removed as subagents inherit $TMUX from parent.

    # Atomic update: validate status, transition to blocked_user, AND set blocked_question
    # Uses exclusive lock to ensure atomicity (addresses P1: non-atomic state updates)
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()

        # Check current status (addresses P1: missing error handling)
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            print(f"Task {task_id} not found in database", file=sys.stderr)
            return ExitCode.NOT_FOUND.value

        current_status = row[0]
        if current_status not in ("in_progress", "blocked_user"):
            print(
                f"Cannot block: task is '{current_status}', expected 'in_progress' or 'blocked_user'",
                file=sys.stderr,
            )
            return ExitCode.INVALID_STATE.value

        # Atomic update of both status AND blocked_question
        # When already blocked_user, this updates the question (allows adding context)
        cursor.execute(
            "UPDATE tasks SET status = 'blocked_user', blocked_question = ? WHERE id = ?",
            (question, task_id),
        )
        conn.commit()

    logger.debug("Task %d: %s -> blocked_user", task_id, current_status)
    print(f"Blocked: {question}")
    print("Human can resolve via: /inbox")
    print('TIP: If another worker could fix this, use: ft work report "title"')
    return 0
