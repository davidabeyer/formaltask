# Worktree Architecture

## Problem Statement

You work in the `formaltask` repository to modify skills, agents, hooks, commands, etc. These must be:
1. **Tracked in git** for version control
2. **Shared globally** via ~/.claude symlinks for Claude Code runtime
3. **Shared across worktrees** without being deleted during merges

## The Challenge: Git Worktree + Symlinks

When merging worktrees back to master, git would see symlinked directories as "deleted files" and try to remove master's .claude/ contents. This is catastrophic.

## Architecture Solution: Multi-Layer Protection

### Layer 1: Source of Truth
```
~/formaltask/ (master branch)
├── agents/             [git tracked - YOU EDIT HERE]
└── .claude/
    ├── commands/       [git tracked - YOU EDIT HERE]
    ├── skills/         [git tracked - YOU EDIT HERE]
    ├── hooks/          [git tracked - YOU EDIT HERE]
    ├── scripts/        [git tracked - YOU EDIT HERE]
    ├── templates/      [git tracked - YOU EDIT HERE]
    ├── epics/          [gitignored - per-epic data]
    └── tdd-guard/      [gitignored - test state]
```

### Layer 2: Global Runtime (Symlinks)
```
~/.claude/
├── agents      → ~/formaltask/agents
├── commands    → ~/formaltask/.claude/commands
├── skills      → ~/formaltask/.claude/skills
├── hooks       → ~/formaltask/.claude/hooks
├── scripts     → ~/formaltask/.claude/scripts
├── templates   → ~/formaltask/.claude/templates
├── projects/   [runtime state - NOT in claude-code]
├── sessions/   [runtime state - NOT in claude-code]
└── logs/       [runtime state - NOT in claude-code]
```

### Layer 3: Worktrees (Symlinks to Master)
```
~/formaltask/bin/wt-ink/
├── agents          → ~/formaltask/agents
└── .claude/
    ├── commands    → ~/formaltask/.claude/commands
    ├── skills      → ~/formaltask/.claude/skills
    ├── hooks       → ~/formaltask/.claude/hooks
    ├── scripts     → ~/formaltask/.claude/scripts
    ├── templates   → ~/formaltask/.claude/templates
    ├── epics/      [worktree-specific - NOT symlinked]
    └── tdd-guard/  [worktree-specific - NOT symlinked]
```

## Protection Mechanisms

### 1. Git Attributes (`.gitattributes`)
```
# Protect .claude directories from being deleted during worktree merges
.claude/commands/** merge=ours
.claude/skills/** merge=ours
.claude/agents/** merge=ours
.claude/hooks/** merge=ours
.claude/scripts/** merge=ours
.claude/templates/** merge=ours
.claude/epics/** merge=ours
```

**What it does:** Forces git to keep master's version during merge conflicts. If a worktree tries to "delete" these directories (due to symlinks), git keeps master's real directories.

### 2. Pre-Merge Hook (`.git/hooks/pre-merge-commit`)
Blocks merge commits that would delete `.claude/*` directories.

**What it does:** Fails the merge if any `.claude/` files are staged for deletion, preventing accidental destruction.

### 3. Git Worktree Exclude (`.git/info/exclude` per worktree)
```
# Symlinked directories - managed by setup script
.claude/commands/
.claude/skills/
.claude/agents/
.claude/hooks/
.claude/scripts/
.claude/templates/
.claude/epics/
```

**What it does:** Tells git to ignore these paths in worktrees (they're symlinks, not real files).

### 4. Skip-Worktree Flags
```bash
git update-index --skip-worktree .claude/commands/**
```

**What it does:** Marks files as "locally modified" so git doesn't try to track changes in worktrees.

## Workflow

### Creating a New Worktree
```bash
cd ~/claude-code
git worktree add bin/feature-name
cd bin/feature-name
```

**Result:** Worktree has symlinks to master's `.claude/` directories. Changes in master are immediately visible in worktree.

### Editing Skills/Agents/Commands
**ALWAYS edit in master:**
```bash
cd ~/claude-code
vim .claude/skills/my-skill/SKILL.md
```

**Changes immediately available:**
- `~/.claude/skills/` (global runtime)
- `~/formaltask/bin/any-worktree/.claude/skills/` (all worktrees)

### Merging Worktrees Back to Master
```bash
cd ~/claude-code
git merge bin/feature-name
```

**Protections activate:**
1. `.gitattributes` forces merge=ours for `.claude/**`
2. `pre-merge-commit` hook blocks if deletions detected
3. Master's `.claude/` directories preserved

### Syncing Latest Changes to Existing Worktrees
Symlinks mean worktrees automatically see master's `.claude/` changes. No manual sync needed.

## Common Issues & Solutions

### Issue: Circular Symlinks
**Symptom:** `commands -> commands`, directory loops.

**Fix:**
```bash
# Remove circular symlinks
find .claude -maxdepth 2 -type l -exec sh -c \
  'target=$(readlink "{}"); case "$target" in */.claude/*) rm "{}" ;; esac' \;
```

### Issue: Merge Tries to Delete .claude/
**Symptom:** Git says "deleted .claude/commands/foo.md" during merge.

**Fix:**
1. Check `.gitattributes` exists and has `merge=ours` rules
2. Check pre-merge hook is installed: `ls -la .git/hooks/pre-merge-commit`
3. Re-run worktree setup script
4. Abort bad merge: `git merge --abort`

## Directory Categories

### Git-Tracked + Symlinked (Edit in Master Only)
- `commands/` - Slash commands
- `skills/` - AI skills
- `agents/` - Subagent definitions
- `hooks/` - Git hooks + Claude Code hooks
- `scripts/` - Shell scripts
- `templates/` - File templates

### Git-Ignored + Per-Worktree (Unique Per Worktree)
- `epics/` - Epic tracking data
- `tdd-guard/data/` - Test state

### Runtime-Only (Not in Git)
- `projects/` - Per-project state
- `sessions/` - Session history
- `logs/` - Debug logs

## Key Principles

1. **Single Source of Truth:** Master branch `.claude/` is the canonical source
2. **Symlinks Everywhere:** Global runtime and worktrees use symlinks to master
3. **Multi-Layer Protection:** Multiple mechanisms prevent accidental deletion
4. **Automatic Propagation:** Changes in master instantly visible everywhere
5. **Per-Worktree Isolation:** Epic/test data unique to each worktree

## Maintenance

### Adding New Shared Directory
1. Create in master: `mkdir .claude/new-dir/`
2. Add to `.gitattributes`: `.claude/new-dir/** merge=ours`
3. Add to setup script: `SYMLINK_DIRS=(...  "new-dir")`
4. Create global symlink: `ln -sf ~/formaltask/.claude/new-dir ~/.claude/new-dir`
5. Re-run setup on existing worktrees

### Verifying Protection
```bash
# Check .gitattributes
cat .gitattributes

# Check pre-merge hook
test -x .git/hooks/pre-merge-commit && echo "✅ Hook installed"

# Check global symlinks
ls -la ~/.claude/ | grep " -> "

# Check worktree symlinks
ls -la bin/wt-ink/.claude/ | grep " -> "
```

## Safety Guarantees

✅ **Cannot accidentally delete master's .claude/** - Blocked by pre-merge hook
✅ **Merge conflicts favor master** - `.gitattributes` merge=ours
✅ **Changes propagate instantly** - Symlinks bypass git
✅ **Worktrees stay in sync** - Single source of truth
✅ **Per-worktree isolation** - TDD state + epics separate

**Result:** Safe, efficient workflow for editing Claude Code configuration while using git worktrees.
