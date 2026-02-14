# Input Validation

## Validation Strategy

- [ ] Allowlist validation (not blocklist)
- [ ] Validation on server-side (not just client)
- [ ] Type checking enforced
- [ ] Length limits enforced
- [ ] Format validation (regex for emails, URLs, etc.)

## File Upload Security

- [ ] File type validated by content (magic bytes), not extension
- [ ] File size limits enforced
- [ ] Files stored outside webroot
- [ ] Filenames sanitized (no path traversal)
- [ ] Uploaded files scanned for malware

**Red Flags:**
```python
# BAD - Path traversal vulnerable
filename = request.form['filename']
path = f"/uploads/{filename}"
open(path, 'wb').write(data)

# GOOD - Sanitized filename
filename = secure_filename(request.form['filename'])
path = os.path.join(UPLOAD_DIR, filename)
if not path.startswith(UPLOAD_DIR):
    raise ValueError("Invalid path")
```
