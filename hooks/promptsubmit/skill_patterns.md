# Skill Thinking Patterns

Distilled mental models from coding skills. Use these patterns to enhance prompts with structured thinking approaches.

---

## debugging

**Mindset:** Root cause, not symptoms. Understand before fixing.

**Questions to ask:**
- Can I reproduce this 100%?
- What changed recently?
- Where does the data come from? (trace backward)
- Is there working code I can compare to?

**Process:**
1. Reproduce consistently first
2. Find a working reference, compare line-by-line
3. Form ONE hypothesis, test ONE variable
4. After 3 failed fixes → question the architecture, not the fix

**Signs of wrong approach:**
- "Let me try this quick fix" without understanding
- Changing multiple things at once
- Fixing where error appears instead of where it originates

---

## researching-comprehensive

**Mindset:** Multiple sources, multiple perspectives. Depth over speed.

**Questions to ask:**
- What are the authoritative sources for this topic?
- What would a skeptic say about each finding?
- Are there conflicting viewpoints? Why?
- What's the recency/relevance of each source?

**Process:**
1. Define what "comprehensive" means for THIS question
2. Gather from multiple source types (docs, papers, code, discussions)
3. Cross-reference findings - contradictions reveal nuance
4. Score source quality: official docs > well-maintained OSS > blog posts

**Signs of wrong approach:**
- Stopping at first result that seems to answer
- All sources from same author/perspective
- No contradictions found (probably not deep enough)

---

## critiquing-exhaustively

**Mindset:** Find the fatal flaw before production does. Devil's advocate.

**Questions to ask:**
- What's the ONE thing that would make this fail in production?
- What assumption hasn't been tested?
- What happens at scale? At edge cases? Under failure?
- Would I bet my job on this working?

**Process:**
1. Understand the intent before finding flaws
2. Look from multiple angles: security, performance, maintainability, correctness
3. Prioritize ruthlessly - ONE blocker matters more than ten nitpicks
4. Deliver verdict: APPROVED (ship it) / FIX_AND_SHIP (minor) / REVISE (blocker)

**Signs of wrong approach:**
- Listing everything wrong without prioritization
- Critiquing style when there's a logic bug
- No concrete verdict or recommendation

---

## best-practices-research

**Mindset:** Evidence over opinion. Current state of the art.

**Questions to ask:**
- What do the maintainers/creators recommend?
- What does production code in top projects do?
- What are the tradeoffs being made?
- What's changed in the last 6-12 months?

**Process:**
1. Check official documentation first (may be outdated)
2. Look at actual usage in respected codebases
3. Consider multiple stakeholder perspectives (dev, ops, security)
4. Acknowledge when "it depends" - document the decision factors

**Signs of wrong approach:**
- Citing 3-year-old blog posts as current best practice
- Ignoring context ("best practice" varies by situation)
- Not checking what the tool creators actually recommend

---

## exploring-approaches

**Mindset:** Multiple valid paths exist. Compare before committing.

**Questions to ask:**
- What's the simplest thing that could work?
- What's the most scalable/flexible approach?
- What's the balanced middle ground?
- What are we optimizing for?

**Process:**
1. Generate at least 3 distinct approaches (not variations)
2. For each: identify strengths, weaknesses, and ideal context
3. Make tradeoffs explicit - there's no universally "best" answer
4. Recommend based on stated constraints

**Signs of wrong approach:**
- Jumping to first idea without considering alternatives
- All options are minor variations of the same approach
- No explicit tradeoff analysis

---

## expert-planner

**Mindset:** Plans are hypotheses. Evidence-based, not wishful.

**Questions to ask:**
- What does the existing code actually do? (read it)
- What are the integration points and dependencies?
- What's the riskiest part of this plan?
- What would falsify my assumptions?

**Process:**
1. Understand current state deeply before planning changes
2. Trace integration points - where does this touch other code?
3. Decompose into tasks that each deliver testable value
4. Identify the critical path and potential blockers
5. Plans should be falsifiable - specify what "done" looks like

**Signs of wrong approach:**
- Planning without reading the actual code
- Vague tasks like "implement the feature"
- No consideration of what could go wrong

---

## security-code-review

**Mindset:** Assume adversarial input. Defense in depth.

**Questions to ask:**
- What can an attacker control? (inputs, headers, URLs, files)
- What happens if this input is malicious/malformed?
- Where are the trust boundaries?
- What's the blast radius if this fails?

**Process:**
1. Map all input sources and trust boundaries
2. Check OWASP Top 10 systematically (injection, auth, XSS, etc.)
3. Classify by severity: P0 (exploit now) to P3 (hardening)
4. Verify fixes don't just move the vulnerability

**Signs of wrong approach:**
- Only checking "obvious" injection points
- Trusting internal APIs without validation
- Fixing symptoms (sanitize output) not causes (validate input)

---

## handling-errors

**Mindset:** All handlers must have visibility. No silent failures.

**Questions to ask:**
- If this fails silently, how would I know?
- What's the appropriate response: fail fast, retry, or degrade?
- What context does the error handler have for debugging?
- Who needs to be notified? (log level matters)

**Process:**
1. Classify: recoverable vs fatal, expected vs unexpected
2. Choose response: ERROR (needs attention), WARNING (degraded), DEBUG (expected fallback)
3. Include context: what was being attempted, what inputs caused this
4. Never bare `except:` - at minimum log what was caught

**Signs of wrong approach:**
- `except Exception: pass`
- Logging without enough context to debug
- Same handling for all error types

---

## idiomatic-style-audit

**Mindset:** Comprehension first. Code should look like it belongs.

**Questions to ask:**
- Would a maintainer recognize this pattern?
- Does this follow the language/framework conventions?
- Is clever code worth the comprehension cost?
- What would the style guide say?

**Process:**
1. Understand what the code is trying to do before judging style
2. Check against language idioms (Pythonic, Go-like, etc.)
3. Look for consistency with surrounding code
4. Prioritize readability over cleverness

**Signs of wrong approach:**
- Enforcing personal style preferences
- Ignoring existing codebase conventions
- Style critiques on code with logic bugs

---

## auditing-deeply

**Mindset:** Comprehension before criticism. Antirez + Go creators philosophy.

**Questions to ask:**
- What is this code actually doing? (trace it)
- Why was it written this way? (check history/comments)
- What invariants must be maintained?
- What happens if assumptions are violated?

**Process:**
1. Read the code completely before forming opinions
2. Trace actual execution paths, not just reading top-down
3. Check edge cases and error paths
4. Separate "different than I'd write" from "actually wrong"

**Signs of wrong approach:**
- Skimming and pattern-matching for issues
- Critiquing without understanding intent
- Conflating style preferences with correctness issues

---

## auditing-code-deeply

**Mindset:** Understand, then critique. Sequential deep dives.

**Questions to ask:**
- What's the contract this code fulfills?
- What are the implicit assumptions?
- How does this interact with the rest of the system?
- What would break if I changed this?

**Process:**
1. Map the module's responsibilities and boundaries
2. Trace data flow through the code
3. Identify coupling points and dependencies
4. Audit correctness, then performance, then style

**Signs of wrong approach:**
- Surface-level scanning for patterns
- Critiquing code you don't understand
- Missing the forest for the trees

---

## simplifying-code

**Mindset:** Less code is better code. Delete before adding.

**Questions to ask:**
- What can I delete entirely?
- Is this abstraction earning its complexity?
- Would inlining make this clearer?
- Is this flexibility ever used?

**Process:**
1. Identify waste: unused code, over-abstraction, premature generalization
2. Apply rule of three: don't abstract until third use
3. Inline small functions that obscure more than they help
4. Delete dead code paths - version control remembers

**Signs of wrong approach:**
- Adding abstraction layers "for flexibility"
- Keeping code "in case we need it later"
- Wrapper functions that just delegate

---

## testing-anti-patterns

**Mindset:** Test behavior, not implementation. Tests should fail for the right reasons.

**Questions to ask:**
- Does this test break if I refactor without changing behavior?
- Am I testing the contract or the implementation?
- Would this test catch a real bug?
- Is this mock necessary or hiding a design problem?

**Process:**
1. Test public interfaces, not private methods
2. Mock at boundaries (I/O, external services), not internal code
3. One assertion per test (conceptually)
4. Test names should describe behavior, not implementation

**Signs of wrong approach:**
- Tests that mirror implementation line-by-line
- Mocking everything including the class under test
- Tests that pass even when code is broken

---

## verifying-claims

**Mindset:** Trust but verify. Evidence over assertion.

**Questions to ask:**
- What would prove this claim false?
- Is this observable in the code/output/logs?
- What's the source of this claim?
- Could there be a simpler explanation?

**Process:**
1. Classify the claim type: factual, behavioral, architectural
2. Choose verification method: code inspection, test execution, log analysis
3. Look for counter-evidence, not just confirmation
4. Document what you checked and found

**Signs of wrong approach:**
- Accepting claims without verification
- Only looking for confirming evidence
- Trusting tool output without sanity check

---

## implementation-evaluator

**Mindset:** Follow the user's path. Entry points to edge cases.

**Questions to ask:**
- What are all the entry points to this feature?
- What's the happy path? What about errors?
- Where do the flows intersect or diverge?
- What assumptions are made about input/state?

**Process:**
1. Enumerate all entry points (CLI, API, UI, internal)
2. Trace each path: happy, error, edge cases
3. Identify gaps: unhandled states, missing validation, dead ends
4. Map the actual flow vs intended design

**Signs of wrong approach:**
- Only checking the main happy path
- Assuming error handling exists without tracing it
- Missing entry points (often: CLI flags, config options)

---

## test-driven-development

**Mindset:** Test first, then code. Red-Green-Refactor.

**Questions to ask:**
- What's the smallest behavior I can test?
- Does this test fail for the right reason?
- Is the implementation minimal to pass this test?
- Is now the time to refactor?

**Process:**
1. RED: Write a failing test for one specific behavior
2. GREEN: Write minimum code to make it pass
3. REFACTOR: Clean up without changing behavior (tests still pass)
4. Repeat: Next behavior, next test

**Signs of wrong approach:**
- Writing code before tests
- Making tests pass by changing the test
- Skipping refactor phase (or refactoring without green tests)
