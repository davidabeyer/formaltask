# Authorization (OWASP A01)

## Access Control

- [ ] Every endpoint checks authorization
- [ ] Deny by default, allow explicitly
- [ ] No client-side-only authorization checks
- [ ] IDOR prevented (can't access other users' data via ID manipulation)
- [ ] Vertical privilege escalation prevented

**Red Flags:**
```python
# BAD - IDOR vulnerability
@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int):
    return db.get_document(doc_id)  # No ownership check!

# GOOD - Authorization check
@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int, user: User = Depends(get_current_user)):
    doc = db.get_document(doc_id)
    if doc.owner_id != user.id:
        raise HTTPException(403)
    return doc
```

## Role-Based Access

- [ ] Roles are checked server-side
- [ ] Admin functions require admin role
- [ ] Role changes require re-authentication
- [ ] Principle of least privilege applied
