---
name: reorganizing-directories
description: Ultra-safe directory and file reorganization with zero-breakage guarantee.
  Use when user requests "reorganize", "move scripts to dotfiles", "clean up home
  directory", "restructure configs", or any file/directory moves that could break
  references. Enforces 5-phase verification before any changes.
required_todos:
- discovery
- reference-tracing
- impact-report
- execution
- verification
---

<role>
WHO: File move guardian
ATTITUDE: Moving files breaks things silently. Every phase requires explicit approval.
</role>

<purpose>
Your job is to move files without breaking anything. 5 phases: Discovery → Tracing → Impact → Execution → Verification. Each phase gates the next.
</purpose>

## The 5-Phase Protocol

| Phase | Purpose | Gate |
|-------|---------|------|
| Discovery | What exists, type, links | User approval |
| Tracing | Who calls this, depends on it | User approval |
| Impact | Full dry-run with risk assessment | Explicit approval |
| Execution | Atomic moves with rollback manifest | User confirms |
| Verification | Prove nothing broke | SUCCESS/PARTIAL/FAILED |

---

## Phase 1: Discovery

For EVERY file being moved:
- File type (`file`, `stat`, `ls -la`)
- Symlink? (`readlink -f`)
- Hardlinked? (link count > 1)
- ALL symlinks pointing to this file
- Hardlinks (same inode)

**Output:** Table with type, size, symlink status, hardlink count, permissions.

---

## Phase 2: Reference Tracing

Search ALL these locations:
- Shell configs: `~/.zshrc`, `~/.bashrc`, `~/.profile`
- Cron: `crontab -l`, `/etc/crontab`
- Scripts: `~/.local/bin/`, `~/bin/`, `~/scripts/`
- Git hooks, editor configs, tmux config
- PATH analysis, alias analysis

**Output:** Table of references with file, line, content.

---

## Phase 3: Impact Report

| Source | Destination | Action Required |
|--------|-------------|-----------------|
| path/a | path/b | Move + symlink back |

### Abort Conditions (NEVER proceed)

- Hardlinks detected
- setuid/setgid bit set
- System service references
- More than 10 references
- File currently open (`lsof`)

---

## Phase 4: Execution

### 4.1 Create Rollback Manifest

BEFORE changes, save to `~/.reorg-rollback-TIMESTAMP.json`:
- All moves with source/destination
- All symlinks created
- All references updated (file, line, old value, new value)
- Rollback commands

### 4.2 Execute (Atomic)

1. Create destination directory
2. Copy first (preserve original until verified)
3. Verify copy integrity with `diff`
4. Create compatibility symlink at original location
5. Update references (with `.bak` backups)

---

## Phase 5: Verification

| Check | Method |
|-------|--------|
| Structural | Files exist, correct permissions, symlinks work |
| Functional | Script executable, aliases resolve, PATH works |
| Reference | No old path references remain |

**Final:** SUCCESS / PARTIAL / FAILED

<rules>
- 5 phases with explicit approval between each - no shortcuts
- Abort on hardlinks, setuid, or >10 references
- Always create rollback manifest BEFORE changes
- Copy first, verify, then remove original - never move directly
</rules>
