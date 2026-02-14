# Spec Validation Steps

Detailed workflow for validating Spec claims against codebase reality.

## Step 1: Extract Spec Content

For each task in the epic, extract validation targets from Spec content:

```python
# Spec content stored in task metadata.artifact_content
task = repository.get_task(task_id)
spec_content = task.get("metadata", {}).get("artifact_content", "")
```

Extract from Spec:
- File paths (e.g., `hooks/lib/auth.py:45-67`)
- Function/class references (e.g., `validate_user()`, `class AuthManager`)
- Import statements (e.g., `from hooks.lib import X`)
- Pattern references (e.g., "follow pattern from `utils.py:12`")
- Library claims (e.g., "uses Pydantic v2 field_validator")

## Step 2: Verify File Existence

For every file path mentioned in Spec:

```python
# To verify file exists
Glob(pattern=file_path)

# For paths with line numbers:
# 1. Strip line numbers: hooks/lib/auth.py:45-67 → hooks/lib/auth.py
# 2. Glob to verify file exists
# 3. If exists, Read to verify line range is valid
```

Classification:
- **P0 Critical**: File does not exist at all
- **P1 High**: File exists but line numbers out of range
- **P2 Medium**: File exists but has moved (found via semantic search)

## Step 3: Verify Symbols

For every function/class/pattern referenced:

```python
# Semantic search to understand context
mcp__auggie-mcp__codebase-retrieval(
    information_request=f"Where is {symbol_name} defined and how is it used"
)

# Exact symbol lookup for precise verification
Grep(pattern=f"def {function_name}|class {class_name}")
```

Classification:
- **P0 Critical**: Symbol does not exist anywhere in codebase
- **P1 High**: Symbol exists but in different location than Spec claims
- **P1 High**: Symbol signature differs from Spec assumption
- **P2 Medium**: Symbol exists but is deprecated

## Step 4: Verify Library Claims

For third-party library claims:

```python
# Resolve library
lib_id = mcp__context7__resolve-library-id(libraryName="library-name")

# Verify specific feature claim
docs = mcp__context7__get-library-docs(
    context7CompatibleLibraryID=lib_id,
    topic="specific feature claimed in Spec"
)

# Cross-reference with real patterns
patterns = mcp__gateway__call_mcp_tool(
    mcp_name="exa", tool_name="get_code_context_exa",
    arguments={"query": f"{library} {feature} production usage gotchas"}
)
```

Classification:
- **P0 Critical**: Library feature doesn't exist as claimed
- **P1 High**: Feature exists but API differs from Spec assumption
- **P2 Medium**: Feature is deprecated, newer alternative available

## Step 5: Check Pattern Consistency

For Specs that reference existing patterns:

```python
# Semantic search for pattern
mcp__auggie-mcp__codebase-retrieval(
    information_request=f"Show me the pattern used in {reference_file}"
)

# Compare with Spec's proposed implementation
# Flag inconsistencies
```

Classification:
- **P1 High**: Spec implementation contradicts referenced pattern
- **P2 Medium**: Spec doesn't follow project conventions
