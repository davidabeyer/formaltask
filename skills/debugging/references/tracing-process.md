# Tracing Process - Detailed Steps

## Step 1: Observe the Symptom

Document where the error appears:
- Exact location (file, line number, function)
- Operation being performed when failure occurs
- Complete error message and stack trace
- Context (what data was being processed)

**Example:**
```
Error: Cannot read property 'tempDir' of undefined
Location: git.ts:147 in initRepo()
Operation: Creating .git directory
Stack: initRepo → setupContext → runTests
```

## Step 2: Find Immediate Cause

Identify the specific code executing when failure occurs:
- What line threw the error?
- What is the immediate cause (null value, undefined, wrong type)?
- What did the code expect vs what it received?

**Example:**
```typescript
// Line that failed
const gitDir = path.join(context.tempDir, '.git');
                         // ↑ context.tempDir is empty string ""
```

## Step 3: Ask: What Called This?

Map the function/method that invoked the problematic code:
- Trace one level up the call stack
- Examine parameters passed to the failing function
- Check where those parameters originated

**Example:**
```typescript
// Calling function
function setupContext(config) {
    const ctx = new Context();  // Creates context with empty tempDir
    initRepo(ctx);              // Passes uninitialized context
}
```

## Step 4: Keep Tracing Upward

Examine values passed through the call chain:
- **Focus on: "What value was passed?"**
- Continue tracing to understand data flow
- Identify where the invalid value was introduced
- Note any transformations along the way

**Example:**
```typescript
// Level 3 up the stack
function runTests() {
    const config = loadConfig();
    setupContext(config);  // Called before tempDir is set
}

// Level 4 - THE ROOT CAUSE
beforeEach(() => {
    runTests();  // Called before test fixture creates tempDir
});
```

## Step 5: Find Original Trigger

Reach the entry point where invalid input originated:
- Identify the source of incorrect data
- Determine why validation didn't catch it
- Understand the sequence of events

**Root cause identified:**
```typescript
// The problem: tempDir accessed before initialization
class Context {
    tempDir = "";  // Default empty string - BAD!

    // Should be:
    get tempDir() {
        if (!this._tempDir) {
            throw new Error("Context not initialized - tempDir accessed before setup");
        }
        return this._tempDir;
    }
}
```

## Decision Flowchart

```
Error occurs deep in call stack
    ├─ Can trace backwards? → YES → Use root-cause tracing
    └─ Can trace backwards? → NO  → Document symptom fix as technical debt
```
