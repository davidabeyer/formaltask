# Formula System

Reusable YAML templates for generating parameterized epic structures. Formulas solve the problem of repeating identical task shapes across epics.

## The problem

Many epics share the same task structure — CRUD for a model, an API endpoint with tests, a migration with rollback. Without formulas, you copy-paste YAML and find-replace entity names. One typo and a task has the wrong title for three weeks.

## Data flow

```
.claude/formulas/crud.yaml          batch-config.yaml
        │                                  │
        ▼                                  ▼
┌─────────────────┐              ┌──────────────────┐
│  ft formula cook │              │  ft formula batch  │
│                  │              │                    │
│  load_template() │              │  batch_cook()      │
│  _substitute_    │              │  (loops entities,  │
│    recursive()   │              │   calls cook per   │
│                  │              │   entity)          │
└────────┬────────┘              └─────────┬──────────┘
         │                                 │
         ▼                                 ▼
    output.yaml                   output-dir/
                                    User.yaml
                                    Task.yaml
```

## Module map

| File | Role |
| --- | --- |
| `formaltask/epics/templates.py` | `substitute_variables()`, `load_template()` — low-level YAML loading and Jinja2 delegation |
| `formaltask/epics/formulas.py` | `batch_cook()` — applies a formula to a list of entity dicts |
| `formaltask/cli/commands/formula.py` | CLI: `list`, `cook`, `batch` subcommands + `cook_formula()`, `_substitute_recursive()` |
| `formaltask/core/rules.py` | `render()` — Jinja2 with `StrictUndefined`. See [Rules Kernel](rules-kernel.md). |

## Variable substitution

Formulas use Jinja2 `{{ VAR }}` syntax. The substitution chain:

```
"Create {{ entity }} model"
        │
        ▼
substitute_variables(template_str, {"entity": "User"})
        │
        ▼
render(template_str, vars)          # formaltask/core/rules.py
        │
        ▼
jinja2.Environment(undefined=StrictUndefined)
        │
        ▼
"Create User model"
```

`StrictUndefined` means a missing variable raises `UndefinedError` immediately — no silent empty strings.

## Recursive substitution

`_substitute_recursive()` in `formula.py` walks nested YAML structures:

- **str** — substitute variables via Jinja2
- **dict** — recurse into each value
- **list** — recurse into each item
- **other** (int, bool, null) — pass through unchanged

This means variables work in deeply nested YAML, not just top-level strings.

## Formula file format

A formula is a YAML file in `.claude/formulas/`:

```yaml
# .claude/formulas/crud.yaml
tasks:
  - title: "Create {{ entity }} model"
    description: "Implement {{ entity }} with fields: {{ fields }}"
    acceptance_criteria:
      - "{{ entity }} model passes validation tests"
  - title: "{{ entity }} API endpoints"
    description: "REST endpoints for {{ entity }}"
```

## CLI commands

| Command | What it does |
| --- | --- |
| `ft formula list` | List available formulas from `.claude/formulas/` |
| `ft formula cook <formula> --set VAR=value --output file.yaml` | Generate one YAML from a formula with variables |
| `ft formula batch <config.yaml> --output dir/` | Generate multiple YAMLs from a batch config |

`cook` resolves the formula by name (tries `<name>.yaml` in `--formulas-dir`) or by path.

## Batch config format

```yaml
# batch-config.yaml
formula: .claude/formulas/crud.yaml
entities:
  - NAME: User
    entity: User
    fields: "name, email, role"
  - NAME: Task
    entity: Task
    fields: "title, status, assignee"
```

`NAME` becomes the output filename: `output-dir/User.yaml`, `output-dir/Task.yaml`.

## Relationship to epics

Formulas are **independent** of epic decomposition. They produce YAML files. Those files can be fed into `ft epic create` or used standalone. The formula system has no knowledge of the epic lifecycle — it's a pure template engine.

## Deployment status

The formula system is implemented in code (`ft formula` CLI), but no formulas are shipped by default. Create `.claude/formulas/` with YAML files to use.

## Not yet implemented

- **`when:` conditionals** — conditional task inclusion based on entity properties
- **`includes:` composition** — formulas that include other formulas

These are spec-only. No code exists for them.

## Files

| Path | Purpose |
| --- | --- |
| `formaltask/epics/templates.py` | Template loading + variable substitution |
| `formaltask/epics/formulas.py` | Batch cook engine |
| `formaltask/cli/commands/formula.py` | CLI entry points + recursive substitution |
| `formaltask/core/rules.py` | Jinja2 render with StrictUndefined |
| `tests/unit/test_formula_engine.py` | Batch cook tests |
| `.claude/formulas/` | Formula YAML files (user-created) |
