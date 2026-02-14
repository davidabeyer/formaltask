# Code Review Output Format

Structure review findings by severity for clear communication.

---

## Severity Levels

### P0 - Critical (Blocks Merge)
Issues that will definitely cause bugs, security vulnerabilities, or data loss.

### P1 - High (Should Fix Before Merge)
Issues likely to cause problems, missing error handling, or logic errors.

### P2 - Medium (Fix Soon)
Code quality issues, missing tests, or maintainability concerns.

### P3 - Low (Nice to Have)
Style suggestions, minor optimizations, or documentation improvements.

---

## Finding Format

```
**[P{N}] {Category}: {Title}**
- File: `path/to/file.py:42`
- Issue: Description of the problem
- Impact: What could go wrong
- Fix: Specific suggestion
```

---

## Example Review

```markdown
## Code Review: auth/login.py

### P0 - Critical

**[P0] Error Handling: SQL Injection Vulnerability**
- File: `auth/login.py:56`
- Issue: User input interpolated directly into SQL query
- Impact: Attackers can bypass authentication or dump database
- Fix: Use parameterized queries: `cursor.execute("SELECT * FROM users WHERE email = ?", (email,))`

### P1 - High

**[P1] Edge Cases: No Rate Limiting**
- File: `auth/login.py:48`
- Issue: No limit on login attempts
- Impact: Allows brute-force password attacks
- Fix: Add rate limiting (e.g., 5 attempts per minute per IP)

### P2 - Medium

**[P2] Code Quality: Function Too Long**
- File: `auth/login.py:30-120`
- Issue: `login()` function is 90 lines with 4 levels of nesting
- Impact: Hard to understand and test
- Fix: Extract `validate_credentials()`, `create_session()`, `log_attempt()` helpers

### Summary
- **Critical Issues**: 1 (SQL injection - must fix)
- **High Issues**: 1 (rate limiting)
- **Medium Issues**: 1 (refactoring)
- **Verdict**: BLOCKED - Fix P0 before merge
```

---

## Related Skills

Load additional skills based on findings:

| Finding Type | Load Skill |
|--------------|------------|
| Security issues | `security-code-review` for deeper analysis |
| Test problems | `hunting-test-antipatterns` for test audit |
| Complexity issues | `simplifying-code` for refactoring guidance |
