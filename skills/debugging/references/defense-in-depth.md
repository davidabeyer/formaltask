# Defense-in-Depth Strategy

After identifying the root cause, implement validation at **multiple layers** to make bugs "impossible" rather than merely fixed.

## Layer 1: Entry Point Validation

```typescript
// Validate at the API boundary
function createProject(config: Config) {
    if (!config.tempDir) {
        throw new Error("Config missing required tempDir");
    }
    // ... proceed
}
```

## Layer 2: Intermediate Function Guards

```typescript
// Validate in functions that accept critical parameters
function setupContext(config: Config) {
    assert(config.tempDir, "setupContext requires config.tempDir");
    const ctx = new Context(config.tempDir);
    return ctx;
}
```

## Layer 3: Pre-Operation Checks

```typescript
// Validate immediately before dangerous operations
function initRepo(context: Context) {
    if (!context.tempDir || context.tempDir.length === 0) {
        throw new Error("Cannot init repo: invalid tempDir");
    }
    const gitDir = path.join(context.tempDir, '.git');
    // ...
}
```

## Layer 4: Constructor/Initialization Validation

```typescript
// Make invalid states unrepresentable
class Context {
    private _tempDir: string;

    constructor(tempDir: string) {
        if (!tempDir || tempDir.length === 0) {
            throw new Error("Context requires non-empty tempDir");
        }
        this._tempDir = tempDir;
    }

    get tempDir(): string {
        return this._tempDir;  // Cannot be accessed in invalid state
    }
}
```

## Python Defense-in-Depth Example

```python
from typing import Optional

class Context:
    """Context with validated tempDir access."""

    def __init__(self, temp_dir: Optional[str] = None):
        self._temp_dir = temp_dir

    @property
    def temp_dir(self) -> str:
        """Get tempDir with validation."""
        if not self._temp_dir:
            raise ValueError("Context not initialized - tempDir accessed before setup")
        if not isinstance(self._temp_dir, str) or len(self._temp_dir) == 0:
            raise ValueError(f"Invalid tempDir: {self._temp_dir!r}")
        return self._temp_dir

    @temp_dir.setter
    def temp_dir(self, value: str):
        """Set tempDir with validation."""
        if not value or not isinstance(value, str):
            raise ValueError(f"tempDir must be non-empty string, got {value!r}")
        self._temp_dir = value
```

## Why Multiple Layers?

- **Layer 1** catches user input errors
- **Layer 2** catches programmer errors during refactoring
- **Layer 3** catches edge cases and timing issues
- **Layer 4** makes invalid states impossible
