---
consumes: [sync-result]
produces: [conflicts-resolved]
optional: true
---

## Phase 5: Conflict Resolution (only if conflicts occur)

**BLOCKING GATE:** `git status` shows merge conflicts.

### CRITICAL: Ours/Theirs Inversion During Rebase

**In a MERGE:** "ours" = your branch, "theirs" = incoming branch
**In a REBASE:** INVERTED! "ours" = upstream (HEAD), "theirs" = your commits being replayed

Since we use `git pull --rebase`, always think in rebase terms:
- `<<<<<<< HEAD` = the upstream/remote version (what we're rebasing onto)
- `>>>>>>> {commit}` = your local commit being replayed

**Never say "ours" or "theirs" to the user.** Always say:
- "Keep HEAD version" (upstream/remote)
- "Keep your commit version" (local changes being replayed)

### Step 1: Gather Context

Run `git fetch` first if not already fetched during the pull.

Then run in parallel:

```bash
# What's on the upstream we're rebasing onto
git log --oneline ORIG_HEAD..HEAD -- {conflicted files}

# What commit is being replayed (shown in conflict marker)
git show --stat {commit-hash-from-marker}

# Recent merged PRs (best-effort — skip silently if gh not available)
gh pr list --state merged --limit 5 2>/dev/null
```

Read each conflicted file to see both sides of every conflict marker.

### Step 2: Build TodoWrite Checklist

Create one todo per conflicted file:

```python
TodoWrite(todos=[
    {"content": "Resolve conflict: path/to/file.py", "status": "pending", "activeForm": "Resolving conflict in path/to/file.py"},
    # ... one per file
])
```

### Step 3: Walk Through Each Conflict

For each conflicted file, mark its todo `in_progress`, then:

1. Show the conflict hunks with clear labels:
   ```
   <<<<<<< HEAD (upstream/remote version)
   ... code ...
   =======
   ... code ...
   >>>>>>> abc123 (your local commit being replayed)
   ```
2. Explain in plain language:
   - **HEAD (upstream):** "{what the remote/upstream has}"
   - **Your commit:** "{what your local commit changed}"
   - **The clash:** "{why both sides touched the same spot}"
3. Propose a resolution with rationale
4. Ask using UNAMBIGUOUS labels:

```python
AskUserQuestion(questions=[{
    "question": "How should we resolve {filename}?",
    "header": "Resolve",
    "options": [
        {"label": "Use proposed resolution", "description": "Apply the suggested merge"},
        {"label": "Keep HEAD (upstream)", "description": "Use the remote/upstream version, discard your changes"},
        {"label": "Keep your commit", "description": "Use your local changes, discard upstream version"},
        {"label": "Manual edit", "description": "I'll tell you exactly what to write"}
    ],
    "multiSelect": False
}])
```

Apply the chosen resolution:
- "Keep HEAD (upstream)": `git checkout --ours {file}` (yes, --ours in rebase = HEAD)
- "Keep your commit": `git checkout --theirs {file}` (yes, --theirs in rebase = your commit)

Mark todo completed. Move to next file.

**NEVER resolve a conflict without explicit user confirmation.**

After all conflicts resolved:

```bash
git add {resolved files}
git rebase --continue
```

Then retry the push if that was the intent.

**EXIT CRITERIA:** All conflicts resolved with user approval. Sync complete.
