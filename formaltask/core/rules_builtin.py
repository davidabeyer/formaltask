"""Builtin completion rules as Rule instances (Task #2874).

Converts the 22 COMPLETION_RULES tuples to Rule instances for use with
the rules kernel (evaluate(), apply_rules()).

DSL translation from old to new format:
- "&" → " AND "
- "!" prefix → "NOT "
- "=" → " == "  (unquoted value)
- "*" (catchall) → "true" with priority=999
- Bare key → key (truthy check)

Rule encoding:
- when: Condition in new DSL format
- then: Phase name
- target: "task.phase" for all completion rules
- priority: 1 if blocks, 0 if doesn't block
- name: Reason string (literal or state key for dynamic lookup)
"""

from formaltask.core.rules import Rule, evaluate

# Orchestration rules for watch daemon (Task #2878)
# These rules are evaluated against in-progress/blocked tasks to trigger actions
# like notifications. Initial rules are conservative with low blast radius.
ORCHESTRATION_RULES: list[Rule] = [
    # Notify if a worker has been running for more than 1 hour
    Rule(
        when="duration > 3600",
        then="Worker running >1hr on task #{{ task_id }}. Check status?",
        target="notify",
        priority=0,
        name="long_running_worker",
    ),
]

# Tool redirect rules (Task #2881)
# These rules block certain tools and suggest alternatives.
# Evaluated by formaltask.validators.tool_redirect
TOOL_REDIRECT_RULES: list[Rule] = [
    Rule(
        when="tool_name == WebSearch",
        then="WebSearch not allowed. Use exa instead.",
        target="tool.block",
        priority=0,
        name="websearch_redirect",
    ),
]

# All 22 completion rules as Rule instances
# Rule encoding: when=condition, then=phase, target="task.phase", priority=blocks, name=reason
BUILTIN_RULES: list[Rule] = [
    Rule(
        when="status == cancelled",
        then="done",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="status == completed",
        then="done",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="blocked",
        then="blocked",
        target="task.phase",
        priority=1,
        name="Task blocked by user question",
    ),
    Rule(
        when="check_docs AND NOT has_docs",
        then="needs_fix",
        target="task.phase",
        priority=1,
        name="documentation_required=true but no doc files in commits",
    ),
    Rule(
        when="check_learnings AND NOT has_learnings",
        then="needs_reflection",
        target="task.phase",
        priority=1,
        name="No learnings captured. Run /reflect.",
    ),
    Rule(
        when="NOT has_reviews",
        then="implementing",
        target="task.phase",
        priority=1,
        name="No reviews exist yet",
    ),
    Rule(
        when="blocking_findings",
        then="needs_fix",
        target="task.phase",
        priority=1,
        name="blocking_reason",
    ),
    Rule(
        when="has_needshuman",
        then="needs_human",
        target="task.phase",
        priority=1,
        name="Critical findings marked needshuman",
    ),
    Rule(
        when="low_findings_exceeded",
        then="needs_fix",
        target="task.phase",
        priority=1,
        name="Too many low-priority findings",
    ),
    Rule(
        when="missing_reviews",
        then="implementing",
        target="task.phase",
        priority=1,
        name="missing_reason",
    ),
    Rule(
        when="stale_reviews",
        then="needs_fix",
        target="task.phase",
        priority=1,
        name="stale_reason",
    ),
    Rule(
        when="check_ac AND ac_failed",
        then="needs_fix",
        target="task.phase",
        priority=1,
        name="ac_failed_reason",
    ),
    Rule(
        when="require_pr_merged AND NOT has_pr",
        then="needs_pr",
        target="task.phase",
        priority=1,
        name="PR required and not found",
    ),
    Rule(
        when="require_pr_merged AND NOT pr_merged",
        then="awaiting_merge",
        target="task.phase",
        priority=1,
        name="PR not merged",
    ),
    Rule(
        when="require_pr_merged AND pr_merged",
        then="done",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="require_pr AND NOT has_pr",
        then="needs_pr",
        target="task.phase",
        priority=1,
        name="PR required and not found",
    ),
    Rule(
        when="require_pr AND pr_merged",
        then="done",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="require_pr",
        then="awaiting_merge",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="NOT has_pr",
        then="needs_pr",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="pr_merged",
        then="done",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="pr_closed",
        then="needs_pr",
        target="task.phase",
        priority=0,
        name=None,
    ),
    Rule(
        when="true",
        then="awaiting_merge",
        target="task.phase",
        priority=999,  # Catchall marker
        name=None,
    ),
]


def apply_completion_rules(rules: list[Rule], state: dict) -> tuple[str | None, str | None, bool]:
    """Apply completion rules and return (phase, reason, allowed).

    Iterates through rules, evaluating each condition against state.
    First match wins. Returns (None, None, True) if no rules match.

    Args:
        rules: List of Rule instances (typically BUILTIN_RULES)
        state: Completion state dict from fetch_completion_state()

    Returns:
        Tuple of (phase, reason, allowed) where:
        - phase: The completion phase ("done", "needs_fix", etc.)
        - reason: Reason string (may be looked up from state if dynamic)
        - allowed: True if completion allowed, False if blocked
    """
    for rule in rules:
        if evaluate(rule.when, state):
            phase = rule.then
            # Look up reason in state if it's a state key, else use literal
            reason = rule.name
            if reason and reason in state:
                reason = state.get(reason)
            # priority encodes blocks: 0 or 999 = doesn't block, else blocks
            allowed = rule.priority in {0, 999}
            return phase, reason, allowed
    return None, None, True
