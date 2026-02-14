# Engineering Philosophy

## Radical Simplicity

> **The goal is code that would be acclaimed at an open source conference.**

Before proposing anything, ask:
1. Could this be half the size?
2. What can I delete instead of add?
3. Would the author of Redis/SQLite include this complexity?

---

## Core Principles (One Line Each)

- **Separation of Concerns:** One purpose per module/function. "What does this do?" = one sentence.
- **High Cohesion, Low Coupling:** Parts work together; modules know little about each other.
- **Interfaces over Implementations:** Depend on what it DOES, not HOW.
- **Explicit over Implicit:** Pass dependencies in. Raise exceptions, don't return None silently.

---

## SOLID (One Line Each)

- **S:** One reason to change per class/function
- **O:** Extend behavior without modifying existing code
- **L:** Subtypes honor parent contracts
- **I:** Many small interfaces > one fat interface
- **D:** High-level modules don't depend on low-level details

---

## Refactoring Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Function length | > 20 lines | Extract helpers |
| Nesting depth | > 3 levels | Early returns |
| Parameter count | > 4 | Rethink API |
| Duplicate code | 3+ times | Extract to shared |

---

## Error Handling

Fail fast, fail loud, fail informatively. Use specific exceptions. Validate at boundaries, trust internals.

---

## TDD as Internal Workflow

TDD is the implementation workflow WITHIN each task, not separate tasks.

**Why:**
- **True parallelism:** Independent deliverables run simultaneously
- **Preserved context:** Agent maintains full understanding throughout
- **Simpler tracking:** One task = one deliverable = one PR

**Red-Green-Refactor cycle:**
1. **RED:** Write failing test first
2. **GREEN:** Minimal code to pass
3. **REFACTOR:** Improve while green

---

## Task Sizing: Deliverables, Not Code Units

> **Anti-pattern:** One task per class. Tasks map to DELIVERABLES, not code units.

**A task is TOO SMALL if:**
- Single class with < 5 methods
- < 100 lines of implementation code
- Wouldn't justify its own PR
- Worker startup overhead (~30s + 5K tokens) > actual coding time

**Merge candidates into single task:**
- Classes in same package that change together (cohesive)
- Multiple small utilities serving same feature
- Tightly coupled components (widget + its container)

**Right-sized task:** 100-500 lines, 30 min - 2 hours of work, one meaningful PR

| Too Small | Right Size |
|-----------|------------|
| "Implement TaskRow widget" | "Extract widgets package with TaskRow, StateGroup, TaskSidebar" |
| "Add validation helper" | "Implement input validation layer" |
| "Create config dataclass" | "Add configuration management with validation" |

---

## Architecture Quality Check

Before creating tasks, verify the approach follows sound principles:

**Layering Check:**
```
┌─────────────────────────────────────────┐
│  Presentation Layer (UI, CLI, API)      │  ← Thin, delegates to domain
├─────────────────────────────────────────┤
│  Application Layer (Use Cases)          │  ← Orchestrates domain objects
├─────────────────────────────────────────┤
│  Domain Layer (Business Logic)          │  ← Pure, no I/O dependencies
├─────────────────────────────────────────┤
│  Infrastructure Layer (DB, Files, Net)  │  ← Implements domain interfaces
└─────────────────────────────────────────┘
```

**Dependency Direction Check:**
- Dependencies should point INWARD (toward domain)
- Domain layer has ZERO external dependencies
- Infrastructure implements interfaces defined in domain

**If violated, FLAG IT:**
```
⚠️  Architecture Warning: Task has domain logic depending on SQLite directly.

Recommendation: Define abstract repository interface in domain layer,
implement SQLiteRepository in infrastructure layer.
```
