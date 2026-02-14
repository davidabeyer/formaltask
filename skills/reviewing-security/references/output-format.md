# Security Review Output Format

## Severity Levels

**P0 - Critical (Immediate Action Required)**
- Exploitable vulnerabilities (SQL injection, RCE)
- Authentication bypass
- Data breach risks

**P1 - High (Fix Before Deploy)**
- Authorization flaws
- Hardcoded secrets
- Weak cryptography

**P2 - Medium (Fix Soon)**
- Missing input validation
- Insecure defaults
- Outdated dependencies with known issues

**P3 - Low (Improve When Possible)**
- Missing security headers
- Minor configuration issues
- Defense-in-depth improvements

## Finding Format

```
**[P{N}] {OWASP Category}: {Title}**
- File: `path/to/file.py:42`
- CWE: CWE-XXX (if applicable)
- Vulnerability: Description of the security issue
- Attack Scenario: How an attacker could exploit this
- Remediation: Specific fix with code example
```

## Example Security Review

```markdown
## Security Review: auth/login.py

### P0 - Critical

**[P0] A03 Injection: SQL Injection in Login**
- File: `auth/login.py:56`
- CWE: CWE-89
- Vulnerability: User email directly interpolated into SQL query
- Attack Scenario: Attacker submits `' OR '1'='1' --` as email to bypass auth
- Remediation:
  ```python
  # Before (vulnerable)
  query = f"SELECT * FROM users WHERE email = '{email}'"

  # After (fixed)
  cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
  ```

### P1 - High

**[P1] A07 Auth Failures: Weak Password Hashing**
- File: `auth/password.py:23`
- CWE: CWE-328
- Vulnerability: Using MD5 for password hashing
- Attack Scenario: Leaked password hashes can be cracked with rainbow tables
- Remediation:
  ```python
  # Before (vulnerable)
  hash = hashlib.md5(password.encode()).hexdigest()

  # After (fixed)
  hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
  ```

### Summary
- **Critical (P0)**: 1 (SQL injection)
- **High (P1)**: 1 (weak crypto)
- **Verdict**: BLOCKED - Fix P0/P1 before any deploy
```
