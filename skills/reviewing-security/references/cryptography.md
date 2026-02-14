# Cryptography (OWASP A02)

## Algorithm Selection

- [ ] No MD5 or SHA1 for security purposes
- [ ] AES-256-GCM for symmetric encryption
- [ ] RSA-2048+ or ECDSA for asymmetric
- [ ] TLS 1.2+ for transport security
- [ ] No custom cryptography implementations

## Key Management

- [ ] Keys are not hardcoded
- [ ] IVs/nonces are random and unique
- [ ] Keys are rotated periodically
- [ ] Old keys are securely destroyed

**Red Flags:**
```python
# BAD - Weak crypto
cipher = DES.new(key, DES.MODE_ECB)  # DES is broken, ECB is insecure

# GOOD - Strong crypto
cipher = AES.new(key, AES.MODE_GCM, nonce=os.urandom(12))
```
