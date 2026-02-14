# Rules Kernel

Unified condition evaluation engine used by completion gating, tool redirection, orchestration, and worker templates.

## The problem

Four subsystems need to evaluate conditions against task state: completion checks, tool redirects, orchestration alerts, and prompt templates. Without a shared kernel, each system implements its own condition parser, comparison logic, and template rendering — four copies of the same bugs.

## Architecture

```
Rule(when, then, target, priority, name)
        │
        ▼
evaluate(condition, context)        ◄── AND / OR / NOT / comparisons / dotted paths
        │
        ▼
apply_rules([rules], context)       ◄── first match wins
        │
        ▼
render(template, context)           ◄── Jinja2 with StrictUndefined
        │
        ▼
(output, target)
```

`apply_rules()` iterates rules in order. First rule whose `when` evaluates true has its `then` rendered and returned with its `target`.

## Module map

| File | Role |
| --- | --- |
| `formaltask/core/rules.py` | `Rule` dataclass, `evaluate()`, `render()`, `apply_rules()`, `render_template_file()` |
| `formaltask/core/rules_builtin.py` | `BUILTIN_RULES` (22 completion), `TOOL_REDIRECT_RULES`, `ORCHESTRATION_RULES`, `apply_completion_rules()` |
| `formaltask/core/rules_config.py` | 9 `FORMALTASK_*` env vars parsed at module load |
| `formaltask/core/completion_state.py` | `fetch_completion_state()` — gathers all state keys for rule evaluation |
| `formaltask/core/completion_config.py` | `CompletionConfig` frozen dataclass, `get_effective_config()` |
| `formaltask/core/completion_check.py` | `check_completion()` — top-level entry point, returns `CompletionCheck` |

## Condition DSL

`evaluate(condition, context)` supports:

| Syntax | Example | Semantics |
| --- | --- | --- |
| `AND` | `check_docs AND NOT has_docs` | Both sides must be true |
| `OR` | `has_pr OR pr_merged` | Either side true |
| `NOT` | `NOT has_reviews` | Negation prefix |
| `==`, `!=`, `>`, `<`, `>=`, `<=` | `status == cancelled` | Compare resolved value to literal |
| Dotted path | `task.metadata.retries` | Resolves nested dict keys |
| Bare key | `blocked` | Truthy check: `bool(context.get(key))` |
| Literals | `true`, `false` | Boolean constants |

Operator precedence: `AND` splits first, then `OR`, then `NOT`. No parentheses — flatten complex conditions into multiple rules.

**None-safety:** Ordered comparisons (`>`, `<`, `>=`, `<=`) return `False` when either operand is `None` (missing key). This means `review_rounds.self-critique >= 2` safely returns `False` when no self-critique rounds exist, rather than crashing. `==` with `None` returns `False`; `!=` with `None` returns `True`.

## Rule sets

### Completion rules (22 builtin + task-level)

`BUILTIN_RULES` in `rules_builtin.py`. Evaluated by `apply_completion_rules()` against state from `fetch_completion_state()`.

Tasks can define custom rules in `metadata.completion_rules` (JSON array of rule objects). These are prepended before `BUILTIN_RULES`, giving them first-match-wins priority. Use case: escalation policies like round caps that trigger `ft work blocked` after N review rounds with persistent findings.

Priority encoding:
- `priority=0` — informational (doesn't block completion)
- `priority=1` — blocks completion
- `priority=999` — catchall (doesn't block)

The `name` field serves double duty: literal reason string OR state key for dynamic lookup. If `name` exists as a key in the state dict, the value is used instead.

### Tool redirect rules

`TOOL_REDIRECT_RULES` — blocks `WebSearch`, suggests exa instead. Evaluated by `formaltask.validators.tool_redirect`.

### Orchestration rules

`ORCHESTRATION_RULES` — notification triggers for the watch daemon. Currently one rule: alert when a worker runs >1 hour.

## Workflow phases

Critique-gated tasks use `task_type=critique-gated` with a `workflow_phase` field:

```
c1 (critique phase)
  │
  ├── verdict_go received → transition_phase → exec
  │
  └── no verdict_go → blocks completion ("complete critique phase first")
  │
exec (execution phase)
  │
  └── normal completion rules apply
```

Two rules handle this:
1. **Transition rule** (priority=0): `task_type == critique-gated AND has_verdict_go AND workflow_phase == c1` → signals ready for exec
2. **Gate rule** (priority=1): `task_type == critique-gated AND workflow_phase != exec AND workflow_phase != done` → blocks completion

Transition rule must come before gate rule in the list so it takes priority when `verdict_go` is present.

## CriterionV2 format

Acceptance criteria stored in the `acceptance_criteria` table with `text` and optional `command` fields. When `check_ac` is enabled, commands are executed via subprocess with 300s timeout. Results populate `ac_results`, `ac_failed`, and `ac_failed_reason` in completion state.

## Template rendering

`render_template_file(name, context)` searches for Jinja2 templates:

1. `~/.claude/templates/` — user overlay (first)
2. `formaltask/workers/templates/` — bundled (fallback)

User templates with parse errors fall back to bundled. `StrictUndefined` catches missing variables immediately — no silent empty strings.

Task metadata `prompt_template` triggers template rendering during worker spawn.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FORMALTASK_BLOCK_PRIORITIES` | `P0,P1` | Comma-separated priorities that block completion |
| `FORMALTASK_MAX_LOW_FINDINGS` | unlimited | Max non-blocking findings before blocking |
| `FORMALTASK_REQUIRE_PR` | `false` | Whether PR is required for completion |
| `FORMALTASK_REQUIRE_PR_MERGED` | `false` | Whether PR must be merged |
| `FORMALTASK_CHECK_FRESHNESS` | `true` | Check review freshness (stale review detection) |
| `FORMALTASK_CHECK_DOCS` | `true` | Check `documentation_required` metadata |
| `FORMALTASK_CHECK_LEARNINGS` | `false` | Require at least one learning captured |
| `FORMALTASK_REQUIRED_REVIEWS` | `code-quality` | Comma-separated required review types |
| `FORMALTASK_CHECK_AC` | `true` | Check acceptance criteria commands |

All parsed at module load in `rules_config.py`. Boolean vars accept `true`, `1`, `yes` (case-insensitive).

## Files

| Path | Purpose |
| --- | --- |
| `formaltask/core/rules.py` | Kernel: Rule, evaluate, render, apply_rules, render_template_file |
| `formaltask/core/rules_builtin.py` | Rule definitions: completion, tool redirect, orchestration |
| `formaltask/core/rules_config.py` | Environment variable parsing |
| `formaltask/core/completion_state.py` | State gathering for completion rules |
| `formaltask/core/completion_config.py` | CompletionConfig dataclass |
| `formaltask/core/completion_check.py` | Top-level check_completion() |
| `formaltask/workers/templates/` | Bundled Jinja2 worker templates |
