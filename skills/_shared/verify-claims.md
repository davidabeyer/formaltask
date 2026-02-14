---
consumes: [raw-findings]
produces: [verified-findings]
optional: true
---
# Verify Claims

Independently verify each claim/finding before passing to synthesis.

## For each claim:

1. **File exists at claimed path?**
   ```python
   Glob(pattern=claimed_path)
   ```

2. **Symbol exists?**
   ```python
   Grep(pattern=claimed_symbol, path=project_root)
   ```

3. **Line content matches?**
   ```python
   Read(file_path=claimed_file, offset=claimed_line, limit=5)
   ```

## Classify

| Verdict | Meaning |
|---------|---------|
| CONFIRMED | Evidence supports claim |
| REJECTED | Evidence contradicts claim |
| MODIFIED | Partially true — adjust severity/description |

Drop REJECTED claims. Downgrade MODIFIED claims. Only CONFIRMED proceed to synthesis.