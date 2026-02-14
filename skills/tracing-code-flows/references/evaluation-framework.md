# Evaluation Framework Reference

Comprehensive methodology, checklists, and heuristics for exhaustive implementation evaluation.

## Phase 1: Discovery Deep Dive

### Entry Point Discovery Checklist

#### CLI Applications
- [ ] Main command and all subcommands
- [ ] Flag/option combinations
- [ ] Positional argument variations
- [ ] Stdin input handling
- [ ] Environment variable overrides
- [ ] Config file loading
- [ ] Interactive prompts
- [ ] Piped input/output modes

#### API Services
- [ ] All HTTP endpoints (GET, POST, PUT, PATCH, DELETE, OPTIONS)
- [ ] WebSocket connections
- [ ] GraphQL queries, mutations, subscriptions
- [ ] gRPC service methods
- [ ] Webhook receivers
- [ ] Health check endpoints
- [ ] Metrics endpoints
- [ ] Admin/internal endpoints

#### Event-Driven Systems
- [ ] Message queue consumers
- [ ] Pub/sub subscribers
- [ ] Event handlers (lifecycle, user, system)
- [ ] Scheduled jobs / cron
- [ ] File watchers
- [ ] Database triggers
- [ ] Webhook senders (outbound)

#### Libraries/Modules
- [ ] Public API surface (exported functions/classes)
- [ ] Factory functions
- [ ] Configuration interfaces
- [ ] Extension points / plugin hooks
- [ ] Callback registrations

### Dependency Mapping Template

```markdown
## External Dependencies

### Databases
| Name | Type | Purpose | Required | Fallback |
|------|------|---------|----------|----------|
| main_db | PostgreSQL | Primary data | Yes | None |
| cache | Redis | Session cache | No | In-memory |

### External APIs
| Service | Purpose | Auth Method | Timeout | Circuit Breaker |
|---------|---------|-------------|---------|-----------------|
| Stripe | Payments | API Key | 30s | Yes |
| SendGrid | Email | API Key | 10s | No |

### Environment Variables
| Variable | Purpose | Required | Default | Validation |
|----------|---------|----------|---------|------------|
| DATABASE_URL | DB connection | Yes | None | URL format |
| API_KEY | Auth | Yes | None | Non-empty |

### Configuration Files
| File | Format | Required | Schema Validated |
|------|--------|----------|------------------|
| config.yaml | YAML | Yes | No |
| .env | dotenv | No | No |
```

## Phase 2: Architecture Analysis

### Coupling Assessment Heuristics

**High Coupling Indicators (Problematic):**
- Component imported by >5 other components
- Function with >7 parameters
- Class with >10 dependencies injected
- Circular import chains
- Global state mutations
- Hard-coded peer component references

**Low Coupling Indicators (Healthy):**
- Interface-based dependencies
- Dependency injection used
- Event-based communication
- Clear module boundaries
- Single responsibility adherence

### Cohesion Assessment Heuristics

**High Cohesion Indicators (Healthy):**
- All methods use most class attributes
- Related functions grouped in same module
- Single clear purpose per file
- Naming reflects unified concept

**Low Cohesion Indicators (Problematic):**
- "Utils" or "Helpers" files with unrelated functions
- Classes with methods that don't interact
- Mixed concerns in single file
- Naming is vague or overloaded

### State Management Evaluation

Questions to answer:
1. **What state exists?**
   - In-memory (globals, singletons, caches)
   - Database (tables, documents)
   - File system (temp files, state files)
   - External (session stores, distributed cache)

2. **State lifecycle:**
   - When is state created?
   - What triggers mutations?
   - When is state cleaned up?
   - What happens on crash/restart?

3. **Consistency:**
   - Are transactions used for multi-step mutations?
   - What happens if step 3 of 5 fails?
   - Is there read-your-writes consistency?
   - Are there race windows between read and write?

4. **Concurrency:**
   - Can multiple processes access same state?
   - Is locking used? What granularity?
   - What's the deadlock risk?
   - Are there optimistic concurrency controls?

## Phase 3: Path Enumeration Details

### Happy Path Template

```markdown
### Path: [ENTRY]-HAPPY-[N]

**Entry Point:** `cli_command --flag value`

**Preconditions:**
- Database is available
- User is authenticated
- Config file exists

**Input:**
- flag: "value"
- stdin: none
- env: DATABASE_URL set

**Execution Steps:**
1. Parse arguments
2. Load config
3. Validate input
4. Query database
5. Process result
6. Format output
7. Return success

**Expected Output:**
- Exit code: 0
- Stdout: formatted result
- Side effects: audit log written

**Actual Handling:** HANDLED
**Test Coverage:** Yes (test_happy_path.py:45)
```

### Error Path Categories

1. **Input Validation Errors**
   - Missing required fields
   - Invalid format/type
   - Out of range values
   - Failed regex patterns
   - Schema validation failures

2. **Authentication Errors**
   - Missing credentials
   - Invalid credentials
   - Expired credentials
   - Insufficient permissions
   - Rate limited

3. **Business Logic Errors**
   - Precondition not met
   - Resource not found
   - Resource already exists
   - State transition invalid
   - Quota exceeded

4. **External Dependency Errors**
   - Connection refused
   - Timeout
   - Rate limited
   - Service unavailable
   - Unexpected response format

5. **System Errors**
   - Out of memory
   - Disk full
   - File permission denied
   - Process limit reached
   - Signal received

### Edge Case Categories

#### Numeric Inputs
- Zero
- Negative numbers
- Maximum integer value
- Minimum integer value
- Floating point precision limits
- NaN, Infinity (if applicable)
- Leading zeros

#### String Inputs
- Empty string
- Whitespace only
- Maximum length
- Unicode characters (emoji, RTL, combining)
- Null bytes
- Control characters
- Very long strings (>1MB)

#### Collection Inputs
- Empty collection
- Single item
- Maximum allowed items
- Duplicate items
- Null items within collection
- Deeply nested structures

#### Temporal Inputs
- Epoch (1970-01-01)
- Far future dates
- Far past dates
- Leap years, leap seconds
- Timezone boundaries
- DST transitions
- Invalid dates (Feb 30)

#### File Inputs
- Empty file
- Binary file when text expected
- Symlink
- Directory when file expected
- No read permission
- File being written by another process
- Very large file
- File with no newline at end

### Adversarial Input Categories

#### Injection Attacks
```
SQL: ' OR '1'='1' --
     '; DROP TABLE users; --
     UNION SELECT * FROM secrets

Command: ; rm -rf /
         | cat /etc/passwd
         $(whoami)
         `id`

Path: ../../../etc/passwd
      ....//....//etc/passwd
      /absolute/path/override

XSS: <script>alert('xss')</script>
     javascript:alert(1)
     <img onerror="alert(1)" src="x">

LDAP: *)(uid=*))(|(uid=*
Template: {{constructor.constructor('return this')()}}
```

#### Type Coercion
```json
{"count": "5"}           // String instead of number
{"enabled": 1}           // Number instead of boolean
{"items": "single"}      // String instead of array
{"config": null}         // Null instead of object
```

#### Resource Exhaustion
- Request body of 1GB
- 10,000 concurrent requests
- Deeply nested JSON (1000 levels)
- Regex with catastrophic backtracking
- Infinite loop triggers
- Memory leak triggers

#### Authentication Bypass
- Missing auth header entirely
- Empty auth token
- Malformed JWT
- Expired token
- Token for different user
- Token with modified claims
- Replayed old token

## Phase 4: Walkthrough Methodology

### Mental Execution Technique

For each path, trace through code as if debugging:

1. **Set mental breakpoint at entry**
   - What's in scope?
   - What's the call stack?

2. **Step through each line**
   - What values do variables hold?
   - Which branch is taken?
   - What side effects occur?

3. **At each function call:**
   - What arguments are passed?
   - What exceptions could it throw?
   - What's the return value?

4. **At each I/O operation:**
   - What could fail?
   - What's the timeout?
   - Is there retry logic?

5. **Track mutations:**
   - What database writes?
   - What file writes?
   - What external API calls?
   - What's in the audit trail?

### State Tracking Template

```markdown
### Walkthrough: [PATH-ID]

| Step | Code Location | Variables | State Changes | Potential Issues |
|------|---------------|-----------|---------------|------------------|
| 1 | main.py:45 | args={...} | None | - |
| 2 | parse.py:12 | config=None | Load config | File missing? |
| 3 | validate.py:30 | valid=True | None | No type check |
| 4 | db.py:55 | conn=<Conn> | Open connection | Timeout risk |
| 5 | query.py:20 | result=[] | None | Empty result? |
```

## Phase 5: Gap Analysis Checklists

### Error Handling Checklist
- [ ] All exceptions caught or explicitly propagated
- [ ] Error messages are actionable
- [ ] Errors don't leak sensitive information
- [ ] Cleanup happens on error (files closed, connections returned)
- [ ] Transactions rolled back on error
- [ ] Error codes/types are consistent
- [ ] Retry logic for transient failures
- [ ] Circuit breakers for cascading failures

### Validation Checklist
- [ ] All user inputs validated
- [ ] All external API responses validated
- [ ] All configuration values validated
- [ ] Validation happens at trust boundaries
- [ ] Validation errors are specific
- [ ] Type coercion is explicit
- [ ] Length/size limits enforced
- [ ] Format/pattern validation present

### Security Checklist
- [ ] Authentication on all protected endpoints
- [ ] Authorization checks for resource access
- [ ] Input sanitization (SQL, HTML, command)
- [ ] Output encoding (HTML, JSON)
- [ ] Sensitive data encrypted at rest
- [ ] Sensitive data encrypted in transit
- [ ] Secrets not logged
- [ ] Secrets not in error messages
- [ ] Rate limiting implemented
- [ ] Audit logging for sensitive operations
- [ ] Session management secure
- [ ] CORS configured correctly

### Reliability Checklist
- [ ] Retry with exponential backoff
- [ ] Circuit breakers for external services
- [ ] Timeouts on all external calls
- [ ] Graceful degradation when services down
- [ ] Idempotency for retryable operations
- [ ] Health check endpoints
- [ ] Liveness vs readiness separation
- [ ] Graceful shutdown handling
- [ ] Resource cleanup on shutdown

### Observability Checklist
- [ ] Logging at entry/exit of key operations
- [ ] Logging includes correlation ID
- [ ] Log levels used appropriately
- [ ] Metrics for latency, throughput, errors
- [ ] Distributed tracing integration
- [ ] Error tracking integration
- [ ] Dashboards exist
- [ ] Alerts configured

### Maintainability Checklist
- [ ] Functions under 50 lines
- [ ] Cyclomatic complexity under 10
- [ ] Clear naming (no abbreviations)
- [ ] Comments explain "why" not "what"
- [ ] No magic numbers/strings
- [ ] No code duplication
- [ ] Tests exist and are meaningful
- [ ] Documentation up to date

## Phase 6: Diagram Standards

See `diagram-templates.md` for complete Mermaid syntax.

### Diagram Requirements

Every evaluation MUST include:
1. **Component dependency graph** - Shows coupling
2. **Primary happy path flow** - Shows main logic
3. **Error handling flow** - Shows failure modes

Should include if applicable:
4. **State transition diagram** - For stateful components
5. **Data flow diagram** - For data pipelines
6. **Sequence diagram** - For complex interactions

## Risk Scoring

### Severity Levels

**CRITICAL (P0)**
- Security vulnerability exploitable without authentication
- Data corruption or loss
- System crash/unavailability
- Compliance violation

**HIGH (P1)**
- Security vulnerability requiring authentication
- Data integrity issues
- Significant functionality broken
- Performance degradation >10x

**MEDIUM (P2)**
- Edge case failures
- Minor data issues
- Functionality degraded but works
- Performance degradation 2-10x

**LOW (P3)**
- Code quality issues
- Missing nice-to-have features
- Minor UX problems
- Documentation gaps

### Exploitability Assessment

For security gaps, assess:
- **Access required:** None / Authenticated / Admin
- **Complexity:** Low / Medium / High
- **User interaction:** None / Required
- **Impact:** Confidentiality / Integrity / Availability

### Prioritization Matrix

```
              Low Impact    Medium Impact    High Impact
High Effort      P3            P2              P1
Med Effort       P3            P2              P0
Low Effort       P2            P1              P0
```
