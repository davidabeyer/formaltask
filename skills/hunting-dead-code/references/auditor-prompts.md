# Hunter Agents

Custom agents for hunting dead code. Each has distinct territory and philosophy.

## Custom Agents Reference

| Hunter | Agent | Territory |
|--------|-------|-----------|
| Import | `dead-code-import-hunter` | Unused imports, redundant imports, over-broad imports |
| Function | `dead-code-function-hunter` | Zero-caller functions, dead parameters |
| Branch | `dead-code-branch-hunter` | Unreachable code, feature flag fossils |
| Artifact | `dead-code-artifact-hunter` | Commented code, stale TODOs |
| Verifier | `adversarial-verifier` | Adversarial verification of findings |
| Synthesis | `findings-synthesis` | Final kill list and health score |

All agents at top level in `agents/`.

---

## Spawning Pattern

**CRITICAL: All 4 hunters in ONE message for true parallelism:**

```python
Task(subagent_type="dead-code-import-hunter", run_in_background=True,
     prompt=f"Target: {target}\nTopology: {topology}\nOutput: {output}")
Task(subagent_type="dead-code-function-hunter", run_in_background=True,
     prompt=f"Target: {target}\nTopology: {topology}\nOutput: {output}")
Task(subagent_type="dead-code-branch-hunter", run_in_background=True,
     prompt=f"Target: {target}\nTopology: {topology}\nOutput: {output}")
Task(subagent_type="dead-code-artifact-hunter", run_in_background=True,
     prompt=f"Target: {target}\nTopology: {topology}\nOutput: {output}")
```

**Wait for ALL to complete before verification.**

---

## Output Format

All hunters output markdown with:

```markdown
# {Hunter} Audit: {target}

## Kill (High Confidence)
### 1. [file:line] `symbol`
**Evidence**: grep output showing no usage
**Safe to delete**: Yes/No + reason

## Suspect (Needs Verification)
### 1. [file:line] `symbol`
**Concern**: What might be using it dynamically
**Verify**: Specific check to run

## Keep (False Positive)
### 1. [file:line] `symbol`
**Why it looks dead**: No direct references
**Why it's live**: Hidden usage mechanism
```

---

## Territory Rules

Hunters stay in their lane:

| Finding Type | Hunter |
|--------------|--------|
| Unused import | import-hunter |
| Zero-caller function | function-hunter |
| Unreachable branch | branch-hunter |
| Commented code | artifact-hunter |

**"NOT Your Territory" sections prevent overlap.**

---

## Token Efficiency

Custom agents load instructions into **subagent context only**, not parent.
Saves ~800-1200 tokens per hunter vs inline prompts.

For 4 hunters + verifier + synthesis: **~5000-7000 tokens saved per hunt.**
