# formaltask/core/

Core domain logic for FormalTask. Pure functions and data structures.

## CompletionConfig

Single source of truth for task completion configuration.

### Design Principle

**"If a function doesn't DECIDE, it shouldn't COMPUTE. Pass values, not responsibilities."**

Config is computed ONCE by `get_effective_config()` and passed as DATA to all consumers. No consumer should compute these values independently.

### Usage

```python
from formaltask.core.completion_config import CompletionConfig, get_effective_config

# Load config once at entry point
config = get_effective_config(task_id=42, db_path=".claude/formaltask.db")

# Pass config as data to consumers
builder = WorkerInstructionBuilder(config=config)
result = builder.for_task_start(task_context)
```

### Fields

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `required_reviews` | `list[str]` | task metadata or global default | Review types to run before completion |
| `check_freshness` | `bool` | global rules | Verify no new commits since last review |
| `require_pr` | `bool` | task metadata or global default | Require PR before completion |
| `require_pr_merged` | `bool` | task metadata or global default | Require PR merged before completion |
| `documentation_required` | `bool` | task metadata | Flag for documentation tasks |
| `check_docs` | `bool` | global rules | Check documentation is updated |
| `check_learnings` | `bool` | global rules | Check learnings are captured |

### Override Priority

1. **Task metadata** (highest) - `metadata.required_reviews`, `metadata.require_pr`, `metadata.require_pr_merged`, `metadata.documentation_required`
2. **Global defaults** - `formaltask/core/rules_config.py`

### Key Files

| File | Purpose |
|------|---------|
| `completion_config.py` | CompletionConfig dataclass and `get_effective_config()` |
| `completion_check.py` | `check_completion()` entry point using rules kernel |
| `completion_state.py` | `fetch_completion_state()` gathers review/PR/findings state |
| `rules_config.py` | Global default values for completion rules |
| `rules_builtin.py` | BUILTIN_RULES using rules kernel DSL |
| `rules.py` | Rules kernel with `evaluate()` condition evaluator |
| `../workers/instructions.py` | Consumer: WorkerInstructionBuilder |
| `../../hooks/session_start/task_context_loader.py` | Consumer: format_context() |

### Anti-Pattern: Hardcoded Fallbacks

**DON'T** hardcode fallback values in consumers:

```python
# BAD: Consumer decides the default
effective_reviews = required_reviews or ["code-quality"]
```

**DO** require callers to provide config:

```python
# GOOD: Caller passes pre-computed config
effective_reviews = list(self._config.required_reviews) if self._config else []
```

### Tests

```bash
pytest tests/core/test_completion_config.py -v
pytest tests/unit/worker/test_worker_instruction_builder.py -v
pytest tests/unit/test_format_context_config.py -v
```
