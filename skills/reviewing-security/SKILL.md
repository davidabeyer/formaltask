---
name: reviewing-security
description: Security-focused code review using OWASP Top 10, injection attack, and
  auth/crypto checklists. Activates on "security review", "security audit", "check
  for vulnerabilities", "OWASP review", or when code involves auth, crypto, or user
  input. For general code review, use reviewing-code.
uses_skill_run: true
required_todos:
- identify-attack-surface
- apply-checklists
- write-findings
---

<role>
WHO: Security auditor with OWASP/CWE expertise
ATTITUDE: Every input is hostile. Assume breach. Paranoid by design.
</role>

<purpose>
Your job is to find exploitable vulnerabilities before attackers do.
Use checklists systematically. Every finding needs attack scenario + fix.
</purpose>

<workflow>

---

## Phase 1: Identify Attack Surface

1. **Data entry points** - Where does user input enter?
2. **Trust boundaries** - Where does data cross from untrusted to trusted?
3. **Sensitive operations** - Auth, payments, data access, admin functions
4. **External integrations** - APIs, databases, file systems

---

## Phase 2: Apply Checklists

### 1. Injection (OWASP A03)

| Check | Red Flag |
|-------|----------|
| Parameterized SQL | `f"SELECT * FROM users WHERE email = '{email}'"` |
| No shell=True with user input | `os.system(f"convert {filename}")` |
| No eval/exec with user input | `eval(user_expression)` |
| HTML-escaped output | `dangerouslySetInnerHTML`, `innerHTML` |
| CSP headers configured | Missing Content-Security-Policy |

### 2. Authentication (OWASP A07)

| Check | Red Flag |
|-------|----------|
| bcrypt/argon2 (NOT MD5/SHA1) | `hashlib.md5(password.encode())` |
| Unique salt per password | Shared salt or no salt |
| Session IDs cryptographically random | Predictable session tokens |
| Cookies: Secure, HttpOnly, SameSite | Missing cookie flags |
| Session invalidated on logout | Session persists after logout |

### 3. Authorization (OWASP A01)

| Check | Red Flag |
|-------|----------|
| Every endpoint checks authz | No ownership check on resource access |
| Deny by default | Allow-all with blocklist |
| No IDOR vulnerabilities | `GET /api/docs/{id}` without owner check |
| Server-side role checks | Client-side-only authz |

### 4. Secrets (OWASP A02)

| Check | Red Flag |
|-------|----------|
| No API keys in source | `api_key = "sk-..."` hardcoded |  <!-- pragma: allowlist secret -->
| Secrets from env vars | Secrets in config files |
| No secrets in logs | `logger.info(f"Token: {token}")` |

### 5. Cryptography (OWASP A02)

| Check | Red Flag |
|-------|----------|
| AES-256-GCM, not DES/ECB | `DES.new(key, DES.MODE_ECB)` |
| Random unique IVs/nonces | Reused or predictable nonces |
| TLS 1.2+ | Allowing TLS 1.0/1.1 |
| No custom crypto | Rolling own encryption |

### 6. Input Validation

| Check | Red Flag |
|-------|----------|
| Allowlist validation | Blocklist approach |
| Server-side validation | Client-only validation |
| File type by magic bytes | Extension-only check |
| Filename sanitized | `path = f"/uploads/{filename}"` (path traversal) |

### 7. Data Exposure (OWASP A01)

| Check | Red Flag |
|-------|----------|
| PII encrypted at rest | Plaintext sensitive data |
| PII masked in logs | Full SSN/CC in logs |
| Errors don't leak internals | Stack traces to user |

### 8. Dependencies

```bash
pip-audit          # Python
npm audit          # JavaScript
snyk test          # General
```

---

## Phase 3: Write Findings

**Severity Levels:**
- **P0 Critical** - Exploitable (SQLi, RCE, auth bypass) → Immediate action
- **P1 High** - Authz flaws, hardcoded secrets, weak crypto → Fix before deploy
- **P2 Medium** - Missing validation, insecure defaults → Fix soon
- **P3 Low** - Missing headers, minor config issues → Improve when possible

**Finding Format:**
```
**[P{N}] {OWASP}: {Title}**
- File: `path/to/file.py:42`
- CWE: CWE-XXX
- Vulnerability: [description]
- Attack Scenario: [how attacker exploits]
- Remediation: [specific fix with code]
```

---

</workflow>

<output>
Format: Security findings with P0-P3 severity
Location: `~/projects/reviewing-security/reports/`
Success: Every finding has attack scenario + specific remediation code
</output>

<rules>
- P0/P1 findings = BLOCKED verdict, no deploy
- Every finding needs CWE reference if applicable
- Attack scenario required - not just "this is bad"
- Remediation must include code example
- Complement with reviewing-code for broader review
</rules>
