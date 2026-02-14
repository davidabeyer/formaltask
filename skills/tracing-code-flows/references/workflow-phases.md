# Workflow Phases

Detailed instructions for each phase of implementation evaluation.

## Phase 1: Discovery & Inventory

**Objective:** Establish complete picture of what exists.

1. **Identify scope boundaries**
   - What directories/files constitute the implementation?
   - What is explicitly out of scope?

2. **Enumerate all entry points**
   - CLI commands and subcommands
   - API endpoints (REST, GraphQL, RPC)
   - Event handlers and hooks
   - Scheduled jobs / cron triggers
   - Message queue consumers
   - File watchers
   - User-facing functions/methods

3. **Create component inventory**
   ```
   | Component | Type | Entry Points | Dependencies | Purpose |
   |-----------|------|--------------|--------------|---------|
   ```

4. **Map external dependencies**
   - Databases, caches, queues
   - External APIs and services
   - File system locations
   - Environment variables required
   - Configuration files

## Phase 2: Architecture Mapping

**Objective:** Understand structural relationships and data flow.

1. **Dependency graph analysis**
   - Which components depend on which?
   - Identify coupling hotspots (components with many dependents)
   - Find orphaned components (unused code)
   - Detect circular dependencies

2. **Data flow tracing**
   - Where does data enter the system?
   - How is it transformed at each step?
   - Where does it exit (storage, response, side effects)?
   - What validation occurs at each boundary?

3. **State management analysis**
   - What state is maintained? (in-memory, database, files)
   - State lifecycle (creation, mutation, cleanup)
   - Consistency guarantees (or lack thereof)
   - Race condition susceptibility

4. **Produce architecture diagram** (Mermaid)
   - See `diagram-templates.md` for patterns

## Phase 3: Path Enumeration

**Objective:** Exhaustively list every execution path.

For each entry point, enumerate:

### Happy Paths (normal successful flows)
- Standard input -> expected output
- All valid parameter combinations
- Successful state transitions

### Error Paths (handled failure modes)
- Validation failures
- Business logic rejections
- External dependency failures
- Timeout scenarios

### Edge Cases (boundary conditions)
- Empty inputs, null values
- Maximum/minimum values
- Unicode, special characters
- Concurrent operations
- First-time vs. repeat operations
- Exactly-at-boundary values

### Adversarial Scenarios (malformed/malicious inputs)
- Injection attempts (SQL, command, path traversal)
- Type coercion attacks
- Overflow/underflow attempts
- Resource exhaustion attempts
- Authentication/authorization bypass attempts
- Timing attacks

### Path Documentation Format
```
Path ID: [ENTRY]-[SCENARIO]-[N]
Entry Point:
Input:
Expected Behavior:
Actual Handling: [HANDLED | PARTIAL | MISSING | UNKNOWN]
Risk Level: [CRITICAL | HIGH | MEDIUM | LOW]
Notes:
```

## Phase 4: Simulated Walkthroughs

**Objective:** Mentally execute each path, tracking state at every step.

For each enumerated path:

1. **Trace execution flow**
   - Function/method call sequence
   - Conditional branches taken
   - Loops and iteration counts
   - Exception handling points

2. **Track state mutations**
   - What variables change?
   - What database writes occur?
   - What files are modified?
   - What external calls are made?

3. **Identify decision points**
   - Where does logic branch?
   - What conditions control branching?
   - Are all branches reachable?

4. **Note observations**
   - Unexpected behaviors discovered
   - Assumptions being made
   - Missing validations
   - Potential race windows
   - Resource leak opportunities

## Phase 5: Gap Analysis

**Objective:** Systematically identify what's missing or broken.

Evaluate against these gap categories:

### Error Handling Gaps
- Uncaught exceptions
- Missing error messages
- Errors swallowed silently
- Inconsistent error formats
- Missing rollback/cleanup on failure

### Validation Gaps
- Inputs not validated
- Outputs not validated
- State not validated before operations
- Missing bounds checking
- Missing type checking

### Security Gaps
- Missing authentication checks
- Missing authorization checks
- Injection vulnerabilities
- Sensitive data exposure
- Missing rate limiting
- Missing audit logging

### Reliability Gaps
- Missing retry logic
- Missing circuit breakers
- No graceful degradation
- Missing health checks
- No idempotency guarantees

### Observability Gaps
- Missing logging at key points
- Missing metrics/instrumentation
- Missing tracing correlation
- Insufficient error context

### Maintainability Gaps
- Missing documentation
- Unclear naming
- Magic numbers/strings
- Duplicated logic
- Overly complex functions

### Completeness Gaps
- Features started but incomplete
- TODO/FIXME comments
- Placeholder implementations
- Missing tests for paths

## Phase 6: Flow Diagramming

**Objective:** Visualize all paths and relationships.

Produce these diagrams (Mermaid format):

1. **Component Dependency Graph**
   - All components as nodes
   - Dependencies as edges
   - Highlight coupling hotspots

2. **Control Flow Diagram** (per major entry point)
   - All decision points
   - All paths through the code
   - Error handling branches

3. **State Transition Diagram** (if stateful)
   - All possible states
   - Transitions and triggers
   - Invalid transition attempts

4. **Data Flow Diagram**
   - Data sources and sinks
   - Transformation steps
   - Validation checkpoints

See `diagram-templates.md` for Mermaid syntax patterns.

## Phase 7: Report Generation

**Objective:** Produce actionable output.

See `report-template.md` for full structure.

### Report Storage Location

```
~/projects/implementation-evaluations/{descriptive-name}-{YYYY-MM-DD}.md
```

Example filenames:
- `formaltask-cli-commands-2025-12-08.md`
- `session-end-worker-lifecycle-2025-12-08.md`
- `authentication-flow-security-2025-12-08.md`
