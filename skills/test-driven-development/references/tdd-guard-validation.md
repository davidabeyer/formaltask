# TDD Guard Installation and Validation

**Source:** `~/formaltask/Documentation/TDD-Guard-Validation.md`

Comprehensive validation to verify TDD Guard is properly installed, configured, and ready to enforce test-driven development.

## Overview

The TDD Guard validation script (`~/.claude/scripts/validate-tdd-guard.py`) verifies complete TDD Guard integration with Claude Code.

**Location:** `~/.claude/scripts/validate-tdd-guard.py`

**Purpose:** Validate that TDD Guard is properly installed, configured, and ready to enforce test-driven development practices during Claude Code sessions.

## What It Checks

### 1. TDD Guard CLI Installation
- Checks multiple common installation paths
- Verifies the binary is executable
- Provides installation instructions if missing

### 2. Hook Configuration (settings.json)
- **PreToolUse Hook:** `tdd-guard validate` (15s timeout)
- **PostToolUse Hook:** `tdd-guard capture-results` (30s timeout)
- **SessionStart Hook:** `tdd-guard init` (5s timeout)
- Warns on timeout misconfigurations

### 3. Bash Permissions
- `Bash(tdd-guard:*)` - TDD Guard CLI commands
- `Bash(pytest:*)` - Python test execution
- `Bash(npm test:*)` - NPM test execution

### 4. Data Directory
- Verifies `~/.claude/tdd-guard/data/` exists
- Checks write permissions

### 5. Python Reporter
- Validates `tdd-guard-pytest` package is installed
- Checks for pytest installation

### 6. Custom Instructions
- Checks for `~/.claude/tdd-guard/data/instructions.md`
- Warns if missing (optional but recommended)

## Usage

### Run Validation

```bash
~/.claude/scripts/validate-tdd-guard.py
```

### Exit Codes

- **0** - All critical checks passed
- **1** - Critical issues found (blocks TDD Guard functionality)

Note: Warnings do not cause failure exit code.

### Sample Output

```
=== TDD Guard Integration Validation ===

→ Checking TDD Guard installation...
  ✓ TDD Guard installed at tdd-guard

→ Checking settings.json configuration...
  ✓ All hooks configured correctly

→ Checking Bash permissions...
  ✓ All required Bash permissions present

→ Checking data directory...
  ✓ Data directory exists and is writable

→ Checking Python pytest reporter...
  ✓ tdd-guard-pytest reporter installed

→ Checking custom instructions file...
  ⚠️  Custom instructions file not found
    This is optional but recommended

=== Validation Summary ===

⚠️  1 Warning(s):
  - Custom instructions file not found

✅ All critical checks passed. Review warnings above.
```

## Features

- **Color-Coded Output:** Green ✓ (success), Red ❌ (error), Yellow ⚠️ (warning)
- **Clear Sections:** Each validation check has its own section
- **Actionable Errors:** Each error includes instructions for fixing
- **Self-Contained:** No external dependencies beyond Python stdlib
- **Path Discovery:** Automatically finds tdd-guard in common locations

## Common Issues

### TDD Guard Not Found

**Error:** `TDD Guard binary not found`

**Fix:**
```bash
npm install -g tdd-guard
```

### Missing Hook Configuration

**Error:** `TDD Guard PreToolUse hook not configured`

**Fix:** Add hook to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "tdd-guard validate",
            "timeout": 15000
          }
        ]
      }
    ]
  }
}
```

### Missing Python Reporter

**Error:** `tdd-guard-pytest reporter not installed`

**Fix:**
```bash
pip3 install tdd-guard-pytest
```

### Missing Bash Permissions

**Error:** `Missing Bash permission: Bash(tdd-guard:*)`

**Fix:** Add to `~/.claude/settings.json`:
```json
{
  "permissions": {
    "allow": [
      "Bash(tdd-guard:*)",
      "Bash(pytest:*)",
      "Bash(npm test:*)"
    ]
  }
}
```

## Integration with CI/CD

The validation script can be integrated into CI/CD pipelines:

```bash
# In your CI script
~/.claude/scripts/validate-tdd-guard.py
if [ $? -eq 0 ]; then
  echo "TDD Guard validation passed"
else
  echo "TDD Guard validation failed"
  exit 1
fi
```

## Troubleshooting

### Script Not Executable

```bash
chmod +x ~/.claude/scripts/validate-tdd-guard.py
```

### Wrong Python Version

The script requires Python 3.7+. Check version:
```bash
python3 --version
```

### Permission Denied

Ensure the script has execute permissions and is owned by your user:
```bash
ls -la ~/.claude/scripts/validate-tdd-guard.py
chmod +x ~/.claude/scripts/validate-tdd-guard.py
```

## Related Documentation

- TDD Guard CLI: [GitHub](https://github.com/tdd-guard/tdd-guard)
- Python Reporter: [PyPI](https://pypi.org/project/tdd-guard-pytest/)
- Claude Code Hooks: `~/.claude/Documentation/Hooks.md`

## Maintenance

The validation script is designed to be self-contained and require minimal maintenance. Update the script when:

1. New TDD Guard hooks are added
2. Required permissions change
3. New validation checks are needed
4. Installation paths change

---

**Created:** 2025-11-02
**Related Issue:** #7 - Create Validation Script
**Script Version:** 1.0.0
