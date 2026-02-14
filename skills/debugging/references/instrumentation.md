# Instrumentation Techniques

When manual tracing stalls, add logging **before dangerous operations**.

## JavaScript/TypeScript Pattern

```typescript
// Add instrumentation BEFORE the operation that might fail
const stack = new Error().stack;
console.error('DEBUG initRepo called:', {
    tempDir: context.tempDir,
    tempDirType: typeof context.tempDir,
    tempDirLength: context.tempDir?.length,
    stack: stack
});

// Now perform the operation
const gitDir = path.join(context.tempDir, '.git');
```

**Critical practice:** Use `console.error()` in test environments since loggers may suppress output.

**Capture output:**
```bash
npm test 2>&1 | grep 'DEBUG'
```

## Python Pattern

```python
import traceback
import sys

# Add instrumentation BEFORE the operation
print(f"DEBUG: operation called with {parameter}", file=sys.stderr)
print(f"DEBUG: context = {context.__dict__}", file=sys.stderr)
traceback.print_stack(file=sys.stderr)

# Now perform the operation
result = dangerous_operation(parameter)
```

**Capture with pytest:**
```bash
pytest -s tests/test_module.py 2>&1 | grep 'DEBUG'
# -s flag disables output capture
```

## When to Add Instrumentation

Add debug logging when:
- Call stack is deep (5+ levels)
- Values mutate through multiple functions
- Timing/initialization order is suspect
- Error message doesn't include context
- Multiple code paths could trigger the issue

**Remove instrumentation after root cause found** - don't leave debug code in production.
