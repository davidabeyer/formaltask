# Secrets Management (OWASP A02)

## Hardcoded Secrets

- [ ] No API keys in source code
- [ ] No passwords in configuration files
- [ ] No secrets in environment variable defaults
- [ ] No secrets in Docker images
- [ ] No secrets in logs or error messages

**Detection Patterns:**
```bash
# Search for potential secrets
grep -rE "(api_key|apikey|secret|password|token|credential)" --include="*.py" --include="*.js"
grep -rE "['\"][A-Za-z0-9+/]{32,}['\"]"  # Base64-like strings
```

## Secret Storage

- [ ] Secrets loaded from environment variables
- [ ] Secrets manager used (Vault, AWS Secrets Manager, etc.)
- [ ] Secrets rotated regularly
- [ ] Different secrets per environment
