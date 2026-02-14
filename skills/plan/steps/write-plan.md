---
consumes: [goal, requirements, discovery-results, decisions]
produces: [plan-file]
---
## Phase 6: Write Plan

**BLOCKING: Validation checklist must pass first.**

### BLOCKING CHECKLIST — Cannot write plan until ALL pass

- [ ] Every codebase claim has file:line reference
- [ ] Every new file has explicit caller identified
- [ ] Original Goal is user's EXACT words
- [ ] Goals use CriterionV2 format: {id: "g-N", current: "...", history: []}
- [ ] Each goal is testable (yes/no)
- [ ] Scope boundaries are explicit (IN/OUT)
- [ ] Every design decision has WHY
- [ ] No "TBD", "TODO", or vague words (appropriate, proper, relevant)
- [ ] A different engineer could implement without asking questions
- [ ] **Model Field Consumer Rule**: If plan adds Pydantic model fields, explicit consumer task planned (tests/unit/test_model_field_consumers.py will fail otherwise)
- [ ] **Replacement Contract Rule**: For each "delete X, create Y": list what Y returns (keys, types, ordering) and verify against what X's consumers read
- [ ] **Phase Atomicity Rule**: Each phase can ship independently — no symbol created in phase N that phase N also imports (circular dep) or that only exists after phase N-1 ships
- [ ] **Required Field Rule**: If making a field required, verify all existing data has it (grep count = expected count)

### Write Plan File

```python
from datetime import datetime, timezone

plans_dir = project_root / ".plans"
plans_dir.mkdir(parents=True, exist_ok=True)
plan_file = plans_dir / f"{project}-plan.yaml"  # Git handles versioning
```

**Plan format (YAML):**
```yaml
schema_version: 1

name: "{Name}"

original_goal: |
  {user's exact words — DO NOT REWORD}

discovery:
  summary: |
    {file:line evidence, integration traces}
  files_identified:
    - path: "path/to/file.py"
      line: 42
      relevance: "description"

requirements:
  problem: "{specific problem description}"
  goals:  # CriterionV2 format - each goal has id, current, history
    - id: "g-1"
      current: "{testable criterion 1}"
      history: []
    - id: "g-2"
      current: "{testable criterion 2}"
      history: []
  scope:
    in:
      - "{what's included}"
    out:
      - "{what's explicitly excluded}"

risk_analysis:
  - risk: "{description}"
    mitigation: "{how to address}"

architecture:
  decisions:
    - decision: "{what we decided}"
      why: "{rationale}"
      tradeoffs: "{what we're giving up}"

phases:
  - name: "{phase name}"
    description: "{rough description — NOT detailed tasks, that's /decompose}"

provenance:
  last_command: "/plan {project}"
  status: "draft"
  updated_at: "{ISO8601 timestamp from datetime.now(timezone.utc).isoformat()}"
```

After writing plan to disk:
```python
Bash(command=f"cd {plans_dir} && git add {plan_file.name} && git commit -m 'plan: {project} round {current_round}'")
```

**EXIT CRITERIA:** Plan written to disk and committed to git.
