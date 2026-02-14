# Injection Prevention (OWASP A03)

## SQL Injection

- [ ] All database queries use parameterized statements
- [ ] No string concatenation in SQL queries
- [ ] ORM queries don't use raw SQL with user input
- [ ] Stored procedures don't build dynamic SQL
- [ ] Database user has minimal required permissions

**Red Flags:**
```python
# BAD - SQL injection vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"

# GOOD - Parameterized query
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

## Command Injection

- [ ] No `shell=True` with user input (Python subprocess)
- [ ] No backticks or `$()` with user input (Bash)
- [ ] No `eval()`, `exec()`, `Function()` with user input
- [ ] System commands use allowlists, not blocklists
- [ ] File paths are validated against allowlist

**Red Flags:**
```python
# BAD - Command injection vulnerable
os.system(f"convert {user_filename} output.png")

# GOOD - Use subprocess with list args
subprocess.run(["convert", validated_filename, "output.png"], check=True)
```

## XSS (Cross-Site Scripting)

- [ ] All user input is HTML-escaped before rendering
- [ ] No `dangerouslySetInnerHTML` with user content (React)
- [ ] No `innerHTML` with user content (vanilla JS)
- [ ] Content-Security-Policy headers configured
- [ ] User-generated URLs validated (no `javascript:`)

## Template Injection

- [ ] Server-side templates don't render raw user input
- [ ] No user input in template syntax positions
- [ ] Sandboxed template engines where possible
