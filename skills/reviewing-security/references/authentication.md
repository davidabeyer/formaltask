# Authentication (OWASP A07)

## Password Handling

- [ ] Passwords hashed with bcrypt/argon2/scrypt (NOT MD5/SHA1)
- [ ] Unique salt per password
- [ ] Work factor is appropriate (bcrypt cost >= 12)
- [ ] Passwords never logged or stored in plaintext
- [ ] Password reset tokens are single-use and time-limited

**Red Flags:**
```python
# BAD - Weak hashing
password_hash = hashlib.md5(password.encode()).hexdigest()

# GOOD - Strong hashing
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

## Session Management

- [ ] Session IDs are cryptographically random (>=128 bits)
- [ ] Sessions invalidated on logout
- [ ] Session fixation prevented (regenerate ID on auth)
- [ ] Session timeout configured
- [ ] Cookies have Secure, HttpOnly, SameSite flags

## Multi-Factor Authentication

- [ ] TOTP secrets stored securely
- [ ] Recovery codes are single-use
- [ ] MFA bypass paths are protected
