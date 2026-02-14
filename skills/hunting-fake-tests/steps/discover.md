---
consumes: [audit-scope]
produces: [test-manifest]
---

**quick:** Quick test file count. List top 10 test files by size.

**full:** Find all test files:
```bash
find . -name "test_*.py" -o -name "*_test.py" -o -name "*.bats" | head -100
```

Group by directory. Count tests per file.

**EXIT CRITERIA:** Test manifest with file counts
