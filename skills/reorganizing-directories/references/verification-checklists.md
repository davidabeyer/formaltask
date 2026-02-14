# Verification Checklists

## Pre-Flight Checklist (Before Phase 1)

- [ ] User has clearly specified source and destination
- [ ] Destination parent directory exists or can be created
- [ ] User has write permissions to both locations
- [ ] No ongoing file operations (builds, syncs, backups)
- [ ] Terminal session is stable (not in tmux that might disconnect)

---

## Phase 1: Discovery Checklist

### For Each File

- [ ] Determined file type (`file` command)
- [ ] Checked if symlink (`-L` test)
- [ ] If symlink, resolved full target path (`readlink -f`)
- [ ] Checked hardlink count (`stat` link count)
- [ ] If hardlinks > 1, found all hardlink locations
- [ ] Recorded permissions (especially executable, setuid, setgid)
- [ ] Recorded ownership (user:group)
- [ ] Recorded size for later verification
- [ ] Checked for extended attributes (`xattr -l` on macOS)
- [ ] Checked for ACLs (`ls -le` on macOS, `getfacl` on Linux)

### Symlink Sweep

Locations to scan for symlinks pointing to target:

```
~/.local/bin/
~/bin/
/usr/local/bin/
~/.config/
~/scripts/
~/.dotfiles/
/opt/homebrew/bin/  (macOS)
```

### Red Flags in Discovery

| Finding | Action |
|---------|--------|
| setuid/setgid bit | ABORT - security risk |
| Hardlink count > 1 | ABORT - cannot safely move |
| File owned by root | ABORT - needs sudo, risky |
| Extended attributes | WARN - may lose metadata |
| ACLs present | WARN - may lose permissions |

---

## Phase 2: Tracing Checklist

### Config Files to Search

Shell:
- [ ] ~/.zshrc
- [ ] ~/.bashrc
- [ ] ~/.profile
- [ ] ~/.zprofile
- [ ] ~/.zshenv
- [ ] ~/.bash_profile
- [ ] ~/.zlogout
- [ ] ~/.bash_logout

Scheduled Tasks:
- [ ] `crontab -l`
- [ ] ~/Library/LaunchAgents/*.plist (macOS)
- [ ] ~/.config/systemd/user/*.service (Linux)

Git:
- [ ] ~/.gitconfig
- [ ] ~/.githooks/
- [ ] All .git/hooks/ in common repos

Editors:
- [ ] ~/.config/nvim/
- [ ] ~/.vimrc
- [ ] ~/.config/Code/User/settings.json
- [ ] ~/.emacs.d/

Tmux:
- [ ] ~/.tmux.conf
- [ ] ~/.tmux/*.conf

Other Scripts:
- [ ] ~/.local/bin/*
- [ ] ~/bin/*
- [ ] ~/scripts/*
- [ ] ~/.dotfiles/**

### Search Patterns

For file `foo.sh`, search for:
- `foo.sh` (exact filename)
- `foo` (without extension - aliases/functions)
- Full path variations:
  - `~/.local/bin/foo.sh`
  - `$HOME/.local/bin/foo.sh`
  - `/Users/username/.local/bin/foo.sh`
  - `${HOME}/.local/bin/foo.sh`

### Reference Types

| Type | Example | Update Strategy |
|------|---------|-----------------|
| Direct path | `/path/to/foo.sh` | sed replacement |
| Alias | `alias f='/path/to/foo.sh'` | Update alias definition |
| Function | `foo() { /path/to/foo.sh }` | Update function body |
| PATH entry | `export PATH="$PATH:/dir"` | Usually keep + symlink |
| Source/dot | `source /path/to/foo.sh` | sed replacement |
| Shebang caller | `#!/path/to/foo.sh` | Rare, update if found |

---

## Phase 3: Impact Assessment Checklist

### Risk Scoring

| Factor | Points |
|--------|--------|
| Each reference found | +1 |
| Reference in cron/launchd | +5 |
| Reference in git hook | +2 |
| File is executable | +1 |
| File has >100 lines | +1 |
| File is sourced (not executed) | +3 |
| More than 5 files depend on it | +5 |

**Risk Levels:**
- 0-3: LOW
- 4-7: MEDIUM
- 8-12: HIGH
- 13+: CRITICAL (manual review required)

### Compatibility Strategy Decision

| Scenario | Strategy |
|----------|----------|
| Few references, all updatable | Move + update refs |
| Many references, stable paths | Move + symlink at old location |
| System-wide tool | Move + add new location to PATH |
| Sourced config file | Move + symlink (sourcing follows symlinks) |

---

## Phase 4: Execution Checklist

### Pre-Execution

- [ ] Rollback manifest created with timestamp
- [ ] All .bak files location recorded
- [ ] Disk space sufficient for copies
- [ ] No files currently open (`lsof` check)

### Per-File Execution

1. [ ] Create destination directory (`mkdir -p`)
2. [ ] Copy with attributes preserved (`cp -a`)
3. [ ] Verify copy checksum matches
4. [ ] Verify permissions match
5. [ ] Create compatibility symlink (if needed)
6. [ ] Remove original only after symlink verified
7. [ ] Update references with backups

### Reference Update Safety

```bash
# ALWAYS create backup before sed
sed -i.bak 's|old|new|g' file

# Verify change was made
diff file file.bak

# For multi-line changes, use ed or full rewrite
```

### Atomicity Rules

- Never delete original until new location verified
- Always have rollback path before destructive operation
- Use mv for atomic same-filesystem moves
- Use cp + rm for cross-filesystem (verify cp first)

---

## Phase 5: Verification Checklist

### Structural Verification

- [ ] New file exists at destination
- [ ] New file has correct permissions
- [ ] New file has correct ownership
- [ ] New file size matches original
- [ ] Compatibility symlink exists (if created)
- [ ] Compatibility symlink resolves correctly
- [ ] No broken symlinks in affected directories

### Functional Verification

- [ ] Executable scripts can run: `script --help` or `script --version`
- [ ] Sourced files parse without error: `zsh -n file`
- [ ] Aliases resolve: `type aliasname`
- [ ] PATH resolution works: `which scriptname`
- [ ] Functions defined: `declare -f funcname`

### Integration Verification

- [ ] New shell sources without errors: `zsh -i -c exit`
- [ ] Cron jobs would find file (check cron's PATH)
- [ ] Git hooks would find file
- [ ] Editor plugins would find file

### Reference Audit

```bash
# Should return NOTHING (old paths eliminated)
rg "old/path" ~/.zshrc ~/.bashrc ~/.tmux.conf

# Should return expected hits (new paths working)
rg "new/path" ~/.zshrc ~/.bashrc ~/.tmux.conf
```

---

## Rollback Procedure

If anything fails:

```bash
# 1. Read rollback manifest
cat ~/.reorg-rollback-*.json

# 2. Restore from backups
mv ~/.zshrc.bak ~/.zshrc

# 3. Remove new files/symlinks
rm /new/path
rm /old/path  # if it's now a symlink

# 4. Restore original from .bak or copy back
mv /new/path /old/path
# OR
cp -a /new/path /old/path && rm /new/path

# 5. Verify restoration
source ~/.zshrc
which scriptname
```

---

## Edge Cases

### File is Both Symlink Target and Contains Symlinks

Resolve the full chain before moving:
```bash
# Get canonical path
realpath "$path"
```

### File Has Space in Name

Always quote paths:
```bash
mv "$source" "$dest"  # Correct
mv $source $dest      # BROKEN if spaces
```

### Moving Across Filesystems

```bash
# Check if same filesystem
df "$source" "$dest"

# If different, cp -a then rm (not mv)
cp -a "$source" "$dest" && rm "$source"
```

### File is Currently Being Written

```bash
# Check for open handles
lsof "$path"

# If open, ABORT and wait
```

### Circular Symlinks

```bash
# Detect circular symlinks
readlink -f "$path"  # Will fail or loop

# Use -e to verify final target exists
readlink -e "$path" || echo "BROKEN OR CIRCULAR"
```
