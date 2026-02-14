---
consumes: [codebase-context, project-paths]
produces: [spec-files]
optional: true
---
# Phase 2: PLAN_TO_SPECS

### Task Sizing Decision Tree
```
1. Standalone PR? NO → merge or split. YES → continue.
2. Single class <5 methods? YES → merge with neighbor. NO → continue.
3. ≥30 min coding? NO → merge with related. YES → RIGHT-SIZED.
```

**Cohesion** (high = good): All functions work on same data? One-sentence explanation?
**Coupling** (low = good): Test in isolation? Other changes won't break it?

### Essential Test Filtering (MANDATORY)

For each criterion: *Would deleting this test let a real bug slip?*
- NO → Delete it. YES → Keep it.

**Hard limits per task:**

| Type | Max |
|------|-----|
| Unit | 3-5 |
| Integration | 1-2 |
| E2E | 0 |

### Dependencies

**Auto-inferred:** Use `$task[N].outputs.key` in inputs -- parser auto-adds N to `depends_on`.

```yaml
# Task 1 declares an output
outputs:
  schema: ".artifacts/schema.json"

# Task 2 references it — depends_on: [1] auto-computed
inputs:
  schema: "$task[1].outputs.schema"
```

**Manual override:** When auto-inference doesn't apply (ordering-only deps):
```yaml
depends_on: [1, 2]    # Explicit task numbers
```

**Prefer auto-inference.** Manual `depends_on` for ordering constraints only.

### Reviews & Doc Flags

| Task Content | Required Reviews |
|--------------|-----------------|
| Default | `code-quality` |
| Auth, credentials | + `security` |
| Database operations | + `sqlite` |
| Loops, large data | + `perf` |
| File paths | + `path-security` |
| State transitions | + `state-machine` |
| Subprocess/shell commands | + `subprocess` |
| Hook validators | + `hook` |
| TUI widgets/bindings | + `tui` |
| Pydantic models/validation | + `schema` |
| Try/except, error recovery | + `error-handling` |
| External API clients | + `api-client` |
| User input, CLI args | + `input-validation` |

`documentation_required: true` when: public API, CLI commands, user-facing behavior.

### Output Layout
```
.plans/
├── {project}-plan.yaml
└── {project}-specs/
    └── task-{N}-{slug}-spec.yaml
```

Write specs to `{spec_dir}/task-{N}-{slug}-spec.yaml`.
Task numbering: sequential integers (1, 2, 3). No dotted IDs.

### Spec Format (YAML)

```yaml
title: "Task N: Title"

summary: |
  One paragraph description.

depends_on: []  # Manual override only — prefer inputs/outputs auto-inference

outputs:          # What this task produces (optional)
  template: "formaltask/workers/templates/task_assignment.md.j2"

inputs:           # What this task consumes — auto-infers depends_on (optional)
  render_fn: "$task[1].outputs.render_fn"

implements:
  - g-1
  - g-2

context: |
  Why this exists, what it affects.

implementation:
  - "Step one"
  - "Step two"

acceptance_criteria:   # MUST use CriterionV2 format (validated by hook)
  - id: c-1           # Pattern: c-{N} (required)
    current: "Description of what must be true"  # (required)
    command: "shell command that exits 0 on pass, 1 on fail"  # (optional)
  - id: c-2
    current: "Another testable criterion"
    command: "pytest tests/unit/test_foo.py -k bar -v --tb=short"

required_reviews:
  - code-quality

testing:  # MUST be list[str], NOT a dict
  - "unit: 3 test functions (test_foo, test_bar, test_baz)"
  - "integration: 1 test for full workflow"
```

**testing Field Format (MANDATORY):**
```yaml
# WRONG - dict format will be REJECTED by Pydantic validator
testing:
  unit: "description"
  integration: null
  e2e: null

# RIGHT - list of strings with type prefix
testing:
  - "unit: 3 test functions (test_create, test_update, test_delete)"
  - "integration: 1 workflow test"

# RIGHT - single item is fine
testing:
  - "unit: 1 test function (test_render_template)"
```

**CriterionV2 Format (MANDATORY):**
```yaml
# WRONG - simple strings will be REJECTED by validator
acceptance_criteria:
  - "Concrete command that exits 0/1"

# RIGHT - CriterionV2 with id, current, optional command
acceptance_criteria:
  - id: c-1                    # c-{N} or g-{N} pattern
    current: "Description"     # What must be true
    command: "test command"    # Optional: exits 0/1
```

**implements field:** Each spec MUST include the goal IDs it addresses. Read from plan.yaml `requirements.goals[].id`.

### TDD Atomicity

**NEVER** split RED/GREEN across tasks:

```yaml
# WRONG - separate test and implementation tasks
- title: "Write failing tests (RED phase)"
- title: "Implement code (GREEN phase)"

# RIGHT - atomic TDD within each task
- title: "Implement auth with tests"
  # TDD within this task: write tests, implement, refactor
```

**EXIT CRITERIA:** Specs written to `{spec_dir}/task-{N}-{slug}-spec.yaml`.
