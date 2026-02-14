# formaltask/epics/

Epic lifecycle management, YAML parsing, and validation for FormalTask.

## Quick Start

```python
from formaltask.epics import create_epic, get_epic, archive_epic

# Create an epic
create_epic(db_path, "my-feature", "Implement feature X")

# Get epic data
epic = get_epic(db_path, "my-feature")

# Archive when complete
archive_epic(db_path, "my-feature")
```

## CRUD Operations

Core functions in `__init__.py`:

```python
from formaltask.epics import (
    create_epic,       # Create new epic
    get_epic,          # Get by name
    update_epic,       # Update description/branch/reviewed_at
    archive_epic,      # Archive epic (force=True for incomplete tasks)
    unarchive_epic,    # Restore archived epic
    get_epic_status,   # Get computed status from VIEW
    mark_reviewed,     # Set reviewed_at timestamp
    list_epics,        # List all epics
)
```

## YAML Parsing

Parse `epic.yaml` files with task dependencies:

```python
from formaltask.epics.yaml_parser import parse_epic, validate_epic_format

# Parse YAML or markdown epic file
tasks = parse_epic(yaml_content)  # Returns list of task dicts

# Validate structure before committing
errors = validate_epic_format(yaml_content)
if errors:
    for e in errors:
        print(f"Line {e.line}: {e.message}")
```

### Supported Formats

| Format | Detected By | Use Case |
|--------|-------------|----------|
| YAML | `specs:` or `tasks:` key | Structured task specs |
| Markdown | `## Task X:` headers | Human-readable specs |

### Dependency Syntax

```yaml
tasks:
  - title: "Setup database"
    depends_on: []  # No dependencies
  - title: "Create models"
    depends_on: [0]  # Depends on task 0
  - title: "Add API"
    depends_on: [0, 1]  # Multiple dependencies
```

Validation rules:
- No forward references (task can only depend on earlier tasks)
- No self-references
- No duplicates
- No circular dependencies

## Validation & Analysis

```python
from formaltask.epics.validation import (
    find_dangling_dependencies,  # Deps on non-existent tasks
    calculate_critical_path,     # Longest dependency chain
    calculate_parallelism_waves, # Tasks per parallel wave
    calculate_file_hotspots,     # Files touched by many tasks
    epic_finalize,               # Run all validation
)

# Check for dangling deps
dangling = find_dangling_dependencies(db_path, "my-epic")
# Returns: [(task_id, missing_dep_id), ...]

# Get critical path length
result = calculate_critical_path(db_path, "my-epic")
# Returns: CriticalPathResult(length=5, path=[1,3,7,12,15])

# Finalize epic (validates + provides analysis)
summary = epic_finalize(db_path, "my-epic")
```

## Planning Workflow

State stored in `planning_state` table with atomic writes (`exclusive=True` locking). Plan files git-versioned via `/plan` and `/revise` skills.

```python
from formaltask.epics.planning import begin_stage, get_round

# Workflow: plan -> critique -> plan-decompose -> critique-specs -> revise-specs -> epic-decompose
round_num = begin_stage("my-project", "critique", db_path)
current_round = get_round("my-project", "critique", db_path)  # Read without incrementing
```

## Models

Pydantic models for YAML validation:

```python
from formaltask.epics.models import TaskSpec, EpicSpec

# Validate epic YAML against schema
spec = EpicSpec.model_validate(yaml_data)
```

## Templates & Formulas

Advanced features for parameterized epics:

```python
from formaltask.epics.templates import substitute_variables, load_template
from formaltask.epics.formulas import filter_conditional_tasks, batch_cook

# Template variable substitution
content = substitute_variables(template, {"feature": "auth", "version": "2.0"})

# Conditional task filtering
tasks = filter_conditional_tasks(all_tasks, {"has_tests": True})
```

## Key Files

| File | Purpose |
|------|---------|
| `__init__.py` | CRUD: create_epic, get_epic, archive_epic, etc. |
| `yaml_parser.py` | Parse YAML/markdown, validate dependencies |
| `validation.py` | Critical path, parallelism waves, finalization |
| `planning.py` | Planning workflow state machine |
| `models.py` | Pydantic models: TaskSpec, EpicSpec |
| `templates.py` | Variable substitution, inheritance |
| `formulas.py` | Conditional tasks, formula composition |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| `EpicFormatError` | Check YAML syntax, use `validate_epic_format()` first |
| Forward reference error | Tasks can only depend on earlier tasks (lower index) |
| "Epic already exists" | Use `get_epic()` to check before `create_epic()` |
| "Cannot archive" | Epic has incomplete tasks — use `force=True` or complete tasks |
| Circular dependency | Use `find_dangling_dependencies()` to debug |

## See Also

- `formaltask/tasks/` — Task lifecycle and dependencies
- `formaltask/cli/commands/epic_*.py` — CLI commands
- `formaltask/types.py` — EpicData, CriticalPathResult types
