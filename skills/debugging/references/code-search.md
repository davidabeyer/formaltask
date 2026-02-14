# Code Search Reference

## Semantic Code Search

Use semantic search to locate error sources in the codebase:

```python
mcp__auggie-mcp__codebase-retrieval(
  information_request="[error message or relevant code pattern] - find source and context"
)
```

## Search Strategies

1. **Error message search** - Search for exact error text
2. **Stack trace search** - Search for function names from stack
3. **Pattern search** - Search for similar error patterns
4. **Context search** - Search for related code that might cause the error
