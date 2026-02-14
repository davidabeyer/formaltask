# skills/ - Detailed Documentation

Custom skills for Claude Code. Skills are contextual prompts that activate proactively when their trigger conditions are met.

> **Location**: This is the SOURCE directory (`formaltask/skills/`), symlinked to `~/.claude/skills/`.
> Project-specific overrides go in `.claude/skills/` (no CLAUDE.md there - use README.md for docs).

## What Are Skills?

Skills are specialized knowledge modules invoked automatically by Claude Code when:
- Current context matches activation triggers (keywords, patterns, scenarios)
- User requests related functionality
- Code tasks benefit from specialized guidance

Skills enable:
- Contextual knowledge injection
- Workflow automation patterns
- Best practice enforcement
- Domain-specific expertise

## Skill Format

Skills are directories containing a `SKILL.md` file with:
- `name` (required): kebab-case identifier
- `description` (required): When to activate, with trigger examples
- `system_prompt`: Instructions defining skill behavior (optional, varies by skill)
- Content body: Guidance, patterns, examples, workflows

## Build & Contract System

The skills system has two distinct phases: **build-time injection** and **runtime enforcement**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SKILL CONFIGURATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐         ┌──────────────────┐                         │
│   │   SKILL.md       │         │   _config.yaml   │                         │
│   │   frontmatter    │         │                  │                         │
│   ├──────────────────┤         ├──────────────────┤                         │
│   │ name: debugging  │         │ defaults:        │                         │
│   │ inherit: [review]│         │   contracts:     │                         │
│   │ tools: [auggie]  │         │     required_    │                         │
│   └────────┬─────────┘         │     todos: [plan]│                         │
│            │                   │                  │                         │
│            │                   │ patterns:        │                         │
│            │                   │   "auditing-*":  │                         │
│            │                   │     inherit: ... │                         │
│            │                   │     contracts:   │                         │
│            │                   │       outputs:   │                         │
│            │                   │       [synth.md] │                         │
│            │                   └────────┬─────────┘                         │
│            │                            │                                    │
│            └──────────┬─────────────────┘                                    │
│                       │                                                      │
│                       ▼                                                      │
│            ┌──────────────────┐                                              │
│            │  Resolution      │                                              │
│            │  Order:          │                                              │
│            │                  │                                              │
│            │  1. Skill FM     │  ◄── Highest priority                        │
│            │  2. Patterns     │                                              │
│            │  3. Defaults     │  ◄── Lowest priority                         │
│            └────────┬─────────┘                                              │
│                     │                                                        │
│         ┌──────────┴──────────┐                                              │
│         │                     │                                              │
│         ▼                     ▼                                              │
│  ┌─────────────┐       ┌─────────────┐                                       │
│  │ BUILD TIME  │       │   RUNTIME   │                                       │
│  │ _build.py   │       │ contract-   │                                       │
│  │             │       │ validator   │                                       │
│  ├─────────────┤       ├─────────────┤                                       │
│  │ • inherit   │       │ • contracts │                                       │
│  │ • tools     │       │   required_ │                                       │
│  │ • hooks     │       │   todos     │                                       │
│  │ • frontmatter│      │   outputs   │                                       │
│  └──────┬──────┘       │   requires_ │                                       │
│         │              │   review    │                                       │
│         ▼              └──────┬──────┘                                       │
│  ┌─────────────┐              │                                              │
│  │ Injected    │              ▼                                              │
│  │ into        │       ┌─────────────┐                                       │
│  │ SKILL.md:   │       │ Stop hook   │                                       │
│  │             │       │ validates:  │                                       │
│  │ <!-- @tools │       │             │                                       │
│  │ -injected-->│       │ • Todos     │                                       │
│  │ <!-- @inj   │       │   complete? │                                       │
│  │ ected -->   │       │ • Outputs   │                                       │
│  └─────────────┘       │   exist?    │                                       │
│                        │ • Review    │                                       │
│                        │   logged?   │                                       │
│                        └─────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Resolution Order

When building a skill, config is resolved in this order (higher wins):

| Priority | Source | Example |
|----------|--------|---------|
| **1 (highest)** | Skill's SKILL.md frontmatter | `inherit: [review]` in debugging/SKILL.md |
| **2** | Pattern match in _config.yaml | `auditing-*` matches auditing-architecture |
| **3 (lowest)** | Defaults in _config.yaml | `contracts.required_todos: [plan]` |

### Build-Time vs Runtime

| Aspect | Build-Time (`_build.py`) | Runtime (`contract-validator.py`) |
|--------|--------------------------|-----------------------------------|
| **When** | `python3 _build.py` | Stop hook (session end) |
| **Reads** | `inherit`, `tools`, `hooks`, `frontmatter` | `contracts` only |
| **Writes** | Injects content into SKILL.md | Blocks stop if contracts violated |
| **Storage** | SKILL.md markers | `~/.claude/tmp/active-skills.json` |

### Configuration Fields

**Build-time fields** (injected into SKILL.md):

| Field | Purpose | Example |
|-------|---------|---------|
| `inherit` | Partials to inject before `</rules>` | `[review, output-paths, subagent-spawn]` |
| `tools` | Tool guidance to inject after `</purpose>` | `[auggie, warpgrep, grep]` |
| `hooks` | Session hooks to merge into frontmatter | `{stop: {command: "..."}}` |
| `frontmatter` | Extra YAML fields for frontmatter | `{uses_skill_run: true}` |

**Runtime fields** (checked by stop hook):

| Field | Purpose | Example |
|-------|---------|---------|
| `contracts.required_todos` | Todo items that must be completed | `[plan]` |
| `contracts.outputs` | Files that must exist in run dir | `[synthesis.md]` |
| `contracts.requires_review` | Must log to skill-reviews/ | `true` |

### Phase → Todo Extraction (Single Source of Truth)

Skills with `## Phase N: Name` headers get `required_todos` auto-generated:

```
## Phase 1: Discovery        →  required_todos:
## Phase 2: Analysis              - discovery
## Phase 3: Synthesis             - analysis
                                  - synthesis
```

**No manual list maintenance.** Phases ARE the todos.

- Build extracts phases from content
- Injects into frontmatter as `required_todos`
- Stop hook validates all todos completed
- Skills with explicit `required_todos` in frontmatter are not overwritten

### Standalone vs Family Skills

**Standalone skills** declare their own config in SKILL.md frontmatter:

```yaml
---
name: debugging
description: Systematic debugging...
inherit:
- review
tools:
- auggie
- warpgrep
- grep
---
```

**Family skills** share config via patterns in _config.yaml:

```yaml
patterns:
  "auditing-*":
    inherit: [output-paths, subagent-spawn]
    tools: [auggie, warpgrep]
    contracts:
      outputs: [synthesis.md]
```

### Common Operations

```bash
# Build all skills (injects partials, tools, hooks)
python3 ~/.claude/skills/_build.py

# Build one skill
python3 ~/.claude/skills/_build.py debugging

# Preview what would be built
python3 ~/.claude/skills/_build.py --dry-run

# List skill configurations
python3 ~/.claude/skills/_build.py --list
```

### Skip Lists

Skills can be excluded from defaults:

```yaml
# _config.yaml
skip_contracts:
  - learning-companion
  - goal-compass
  - plan
```

## Directory Structure

```
skills/
├── agent-creator/                    # Create agents
│   └── SKILL.md
├── skill-creator/                    # Create skills
│   └── SKILL.md
├── code-reviewer/                    # Code review guidance
│   └── SKILL.md
├── critical-thinking/                # Decision-making frameworks
│   └── SKILL.md
├── deep-reading-framework/           # Information synthesis
│   └── SKILL.md
├── test-driven-development/          # TDD patterns
│   └── SKILL.md
└── [skill-name]/                     # Individual skill
    └── SKILL.md
```

## Using Skills

Skills activate automatically via the Claude Code skill system:

```
User: "Create a new agent for API validation"
       ↓
Claude Code detects: keyword "agent", context "create"
       ↓
Skill(agent-creator) activates automatically
       ↓
Specialized guidance + system prompts applied
```

Skills can also be explicitly invoked:

```python
Skill("agent-creator")  # Direct invocation
```

## Skill Categories

### Development Infrastructure

| Skill | Purpose | Activates When |
|-------|---------|----------------|
| `agent-creator` | Create agents | "create agent", "new agent" |
| `skill-creator` | Create skills | "create skill", "new skill" |
| `code-reviewer` | Code review | "review code", "code review", "PR" |

### Workflow Patterns

| Skill | Purpose | Activates When |
|-------|---------|----------------|
| `test-driven-development` | TDD guidance | "test first", "TDD", "unit test" |
| `formaltask-workflow-advisor` | FormalTask patterns | "workflow", "best practices" |
| `implementation-evaluator` | Implementation quality | "evaluate", "assess code" |

### Thinking & Analysis

| Skill | Purpose | Activates When |
|-------|---------|----------------|
| `critical-thinking` | Decision frameworks | "decision", "trade-off", "choice" |
| `deep-reading-framework` | Complex analysis | "understand", "analyze document" |
| `critiquing-exhaustively` | Comprehensive technical review | "critique", "exhaustive analysis", explicit invocation |
| `root-cause-tracing` | Problem diagnosis | "bug", "error", "root cause" |

### Documentation & Communication

| Skill | Purpose | Activates When |
|-------|---------|----------------|
| `documentation-updater` | Docs maintenance | "update docs", "documentation" |
| `claudemd-optimizer` | CLAUDE.md lifecycle | "generate CLAUDE.md", "optimize documentation", uses Dynamic-N pattern |
| `technical-doc-review` | Doc quality | "doc review", "documentation review" |
| `system-prompt-writer` | Prompt design | "write prompt", "system prompt" |
| `critiquing-exhaustively` | Technical critique | explicit invocation for comprehensive analysis with orthogonal persona reviewers |

### Research & Exploration

| Skill | Purpose | Activates When |
|-------|---------|----------------|
| `context-priming` | Domain expertise building | "prime context on", "become expert in", "deep dive into [area]", "understand [module]" |
| `researching-comprehensive` | Deep research | "research", "investigate", "explore" |
| `repository-analyzer` | Codebase analysis | "analyze repo", "understand codebase" |
| `code-search-protocol` | Code discovery | "find code", "search implementation" |

## Skill File Format

```markdown
---
name: skill-name
description: >
  ACTIVATE when [trigger condition].
  PROACTIVELY apply when [context pattern].
  Examples: "[user says X]" → [behavior]
---

# Skill Title

Brief description of what this skill provides.

## When to Use

Conditions that trigger this skill's activation.

## Core Principles

1. **Principle 1**: Description
2. **Principle 2**: Description
3. **Principle 3**: Description

## Workflows

### Workflow Name
Steps and patterns for this workflow.

## Examples

Code samples, templates, or reference implementations.

## Best Practices

- Point 1
- Point 2
- Point 3

## Related Skills

- `other-skill-name`: Cross-references
```

### YAML Frontmatter Reference

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | kebab-case identifier |
| `description` | Yes | WHEN to activate (include examples) |
| `system_prompt` | No | Custom system instructions |
| `keywords` | No | Activation keywords |
| `tags` | No | Categorization tags |

## Creating New Skills

### 1. Create Directory

```bash
mkdir -p skills/my-skill
```

### 2. Create SKILL.md

```markdown
---
name: my-skill
description: >
  ACTIVATE when [specific scenario].
  Use PROACTIVELY when [trigger pattern].
  Examples: "[user says X]" → [behavior]
---

# My Skill

Clear, focused guidance on this skill area.

## When to Use

Conditions that trigger activation.

## Workflows

Step-by-step processes this skill enables.

## Examples

Concrete examples and templates.

## Best Practices

Recommended patterns and anti-patterns.
```

### 3. Test Activation

```python
Skill("my-skill")  # Verify it works
```

### 4. Document in This File

Add entry to the appropriate category table above.

## Activation Triggers

Skills activate automatically when:

1. **Keyword Match**: Keywords in user message or code context
2. **Pattern Recognition**: Code patterns Claude recognizes
3. **Scenario Detection**: Inferred situation (e.g., debugging context)
4. **Explicit Invocation**: `Skill("skill-name")`
5. **Hook Context**: Skill context passed via Claude Code hooks

## Best Practices

- **Single focus**: One clear purpose per skill
- **Reusable patterns**: Workflows applicable across projects
- **Clear triggers**: Obvious when skill should activate
- **Practical examples**: Include real-world usage patterns
- **Cross-linking**: Reference related skills
- **No duplication**: Avoid overlapping with agent/command functionality

## Common Gotchas

1. **Activation conflicts**: Overlapping triggers between skills
2. **Scope creep**: Skills becoming too broad (split into multiple)
3. **Stale examples**: Update examples when patterns evolve
4. **Missing keywords**: Skills not activating because of narrow triggers
5. **Tool assumptions**: Skills can't assume specific tools (unlike agents)
6. **Parallel delegation messaging**: All parallel Task invocations MUST be in a SINGLE message for true parallel execution. Sequential messages create sequential execution, defeating the purpose.
7. **Component research scope creep**: When using component-based research (Option C), ensure components are truly independent and non-overlapping. Overlapping scopes lead to duplicated findings and synthesis confusion.

## Parallel Subagent Delegation Pattern

Some complex skills use **parallel subagent delegation** for systematic analysis across multiple perspectives:
- `critiquing-exhaustively`: 5-6 orthogonal persona reviewers with hard limits
- `claudemd-optimizer`: Dynamic-N directory-specific handoffs

### Pattern Overview

1. **Main Agent**: Orchestrates the overall workflow, creates handoff files
2. **Subagents**: Execute specialized analysis tasks in parallel with complete context
3. **Handoff Files**: Bridge the context gap since subagents have zero access to parent conversation

### Handoff Templates

Skills requiring parallel delegation can use handoff templates in two forms:

**Generic Template:** For general parallel delegation
```
skills/{skill-name}/references/handoff-template.md
```

**Persona-Based Templates:** For specialized analysis (like critiquing-exhaustively)
```
skills/critiquing-exhaustively/references/
├── persona-prompts.md      # 6 orthogonal persona prompts
├── ultrathink-prompts.md   # Adversarial reviewer for high-stakes
└── output-format.md        # JSON schema for findings
```

**Discovery-Stream Templates:** For systematic codebase analysis (like context-priming)
```
skills/context-priming/references/discovery-handoffs/
├── discovery-1-documentation.md    # Glob + Read for CLAUDE.md hierarchy
├── discovery-2-semantic.md         # codebase-retrieval for conceptual search
├── discovery-3-flow.md             # warp_grep for multi-file flows
├── discovery-4-pattern.md          # Grep for symbols and patterns
├── discovery-5-test.md             # Glob + Read for test analysis
├── discovery-output-format.md      # Standardized output format
└── handoff-template.md             # Generic template base
```

Both template types address known gotchas:
- **Subagent isolation**: Provides complete context in each handoff file
- **Output collision**: Specifies exact output paths to prevent conflicts
- **Scope creep**: Explicit IN SCOPE / OUT OF SCOPE boundaries
- **Tool usage patterns**: Required Read() → analyze → Write() workflow
- **Quality control**: Built-in checklists and verification steps
- **Lens specialization**: Each template includes lens-specific checklists and severity guidelines

### Implementation Pattern

**Option A: Dynamic handoff creation (generic template)**
```python
# 1. Create handoff files for each lens/stream
for lens in parallel_lenses:
    handoff_path = f"/tmp/handoff-{lens.name}.md"
    Write(file_path=handoff_path, content=populate_template(lens))

# 2. Launch subagents in parallel
for lens in parallel_lenses:
    Task(description=f"{lens.name} analysis",
         prompt=f"Read {handoff_path} and execute the analysis",
         subagent_type="general-purpose",
         run_in_background=True)
```

**Option B: Orthogonal persona templates (critiquing-exhaustively style)**
```python
# 1. Launch orthogonal personas in parallel (ALL in SINGLE message)
Task(description="Devil's Advocate review", subagent_type="general-purpose", ...)
Task(description="Gap Finder review", subagent_type="general-purpose", ...)
Task(description="antirez Reviewer", subagent_type="general-purpose", ...)
Task(description="Doc Verifier", subagent_type="general-purpose", ...)
Task(description="Integration Auditor", subagent_type="general-purpose", ...)

# 2. Each persona has "NOT Your Territory" section to prevent overlap
# 3. Hard limits: max 1 blocker, 3 polish, 3 skipped per persona
# 4. Collect and synthesize results
```

**Option C: Component-based research (researching-comprehensive pattern)**
```python
# 1. Decompose research question into 3-5 independent components
components = decompose_research_question(question)

# 2. Create handoff files using generic template
output_dir = "/tmp/research-output"
task_ids = []

for i, component in enumerate(components, 1):
    handoff_path = f"{output_dir}/handoff-{i}-{component.slug}.md"
    output_path = f"{output_dir}/component-{i}-{component.slug}.md"

    # Fill handoff template with component-specific context
    handoff_content = fill_template("references/handoff-template.md", component)
    Write(file_path=handoff_path, content=handoff_content)

    # Launch researcher for this component
    task_id = Task(description=f"Research: {component.name}",
                   prompt=f"Read {handoff_path} and execute the research task",
                   subagent_type="general-purpose",
                   run_in_background=True)
    task_ids.append(task_id)

# 3. Collect component findings and synthesize
component_findings = []
for task_id in task_ids:
    result = TaskOutput(task_id=task_id)
    component_findings.append(read_component_output(result))

synthesized_report = synthesize_research_findings(component_findings)
```

**Option D: Directory-specific handoffs (Dynamic-N pattern)**
```python
# 1. Identify directories for parallel processing
directories = [
    {"path": "src/lib/", "type": "library-package"},
    {"path": "tests/", "type": "test-suite"},
    {"path": "api/", "type": "api-routes"},
]

# 2. Create handoff files from directory-specific templates
for dir in directories:
    handoff = populate_template(
        template=f"references/directory-handoffs/{dir['type']}.md",
        target_directory=dir['path']
    )
    Write(file_path=f"/tmp/handoff-{dir['type']}.md", content=handoff)

# 3. Launch N parallel subagents (CRITICAL: single message)
Task(description="Generate lib/ CLAUDE.md",
     prompt="Read /tmp/handoff-library-package.md and generate CLAUDE.md",
     subagent_type="general-purpose")
Task(description="Generate tests/ CLAUDE.md",
     prompt="Read /tmp/handoff-test-suite.md and generate CLAUDE.md",
     subagent_type="general-purpose")
# ... N more Task calls in SAME message
```

**Option E: Phase-based orchestration with tool-specific streams (context-priming style)**
```python
# 1. Create output directory structure
output_dir = f"context-priming-output/{target_slug}-{timestamp}"
os.makedirs(f"{output_dir}/handoffs", exist_ok=True)
os.makedirs(f"{output_dir}/outputs", exist_ok=True)

# 2. Write discovery-specific handoff files
discovery_streams = [
    ("discovery-1-documentation.md", "Documentation discovery using Glob + Read"),
    ("discovery-2-semantic.md", "Semantic discovery using codebase-retrieval"),
    ("discovery-3-flow.md", "Flow discovery using warp_grep"),
    ("discovery-4-pattern.md", "Pattern discovery using Grep"),
    ("discovery-5-test.md", "Test discovery using Glob + Read"),
]

for handoff_file, description in discovery_streams:
    handoff_content = populate_discovery_template(handoff_file, target_area, output_dir)
    Write(file_path=f"{output_dir}/handoffs/{handoff_file}", content=handoff_content)

# 3. Launch ALL 5 subagents in SINGLE message (true parallel execution)
task_ids = []
for i, (handoff_file, description) in enumerate(discovery_streams, 1):
    task_id = Task(
        description=f"Discovery {i}: {description.split()[0]}",
        prompt=f"Read handoff file and execute discovery: {output_dir}/handoffs/{handoff_file}",
        subagent_type="general-purpose",
        run_in_background=True
    )
    task_ids.append(task_id)

# 4. Aggregate results from all streams
aggregated_findings = {}
for task_id in task_ids:
    result = TaskOutput(task_id=task_id)
    output_file = extract_output_file_from_result(result)
    findings = Read(file_path=output_file)
    aggregated_findings[task_id] = findings

# 5. Synthesize expert knowledge across all discovery streams
synthesis = synthesize_context_expertise(aggregated_findings, target_area)
Write(file_path=f"{output_dir}/synthesis.md", content=synthesis)
```

### When to Use

**Generic Template (Option A):**
- **Ad-hoc analysis**: Different perspectives each time
- **Flexible scope**: Requirements vary per execution
- **Simple delegation**: Basic parallel task breakdown

**Orthogonal Persona Templates (Option B):**
- **Standardized analysis**: Same persona set every time (like critiquing-exhaustively's 5-6 personas)
- **Distinct territories**: Each persona has unique focus with "NOT Your Territory" sections
- **Complex systematic critique**: Exhaustive analysis with hard output limits per persona
- **Quality assurance**: When consistent prioritization and agent-executable output is critical

**Component-Based Research (Option C):**
- **Multi-faceted research**: Questions with 3-5 distinct aspects to investigate
- **Independent research streams**: Components can be researched without dependencies
- **Comprehensive topic coverage**: Breaking complex topics into manageable pieces
- **Source diversity**: Each component finds different types of sources

**Directory-Specific Handoffs (Option D - Dynamic-N Pattern):**
- **Codebase documentation**: Generating subdirectory CLAUDE.md files
- **Directory-specific workflows**: Each directory type has distinct patterns (api/, tests/, cli/)
- **Variable N scaling**: Number of parallel tasks determined by codebase structure
- **Template specialization**: Pre-built templates for common directory types

**Phase-Based Orchestration (Option E):**
- **Tool-specific streams**: Each discovery stream focuses on different tool capabilities (Glob, Grep, semantic, flow)
- **Context building**: Building domain expertise through systematic codebase discovery
- **Token efficiency**: 60-70% reduction via parallel subagent execution (~40K → 10K main agent tokens)
- **Structured synthesis**: 6-phase pattern with aggregation and expert knowledge synthesis

**When to Use Parallel Delegation (Any Option):**
- **Multiple analysis perspectives**: Technical, security, performance, workflow lenses
- **Parallel processing**: When analysis can be decomposed into independent tasks
- **Large context**: When distributing work reduces main agent token consumption

### Sequential Fallback Mode

Skills using parallel delegation should implement a **sequential fallback** for when the Task tool is unavailable:

```python
# Check if parallel delegation is available
try:
    # Attempt parallel delegation
    task_ids = []
    for analysis in parallel_analyses:
        task_id = Task(description=analysis.name,
                      prompt=analysis.prompt,
                      subagent_type="general-purpose",
                      run_in_background=True)
        task_ids.append(task_id)

    # Collect parallel results
    for task_id in task_ids:
        result = TaskOutput(task_id=task_id)
        process_result(result)

except ToolUnavailableError:
    # Fallback: Run analyses sequentially in main agent
    for analysis in parallel_analyses:
        result = execute_analysis_in_main_agent(analysis)
        process_result(result)
```

**When to use sequential fallback:**
- Task tool temporarily unavailable
- User explicitly requests sequential execution
- Context size constraints prevent parallel handoffs
- Debugging parallel delegation issues

### Sequential Fallback Mode

Skills using parallel delegation should implement a **sequential fallback** for when the Task tool is unavailable:

```python
# Check if parallel delegation is available
try:
    # Attempt parallel delegation
    task_ids = []
    for analysis in parallel_analyses:
        task_id = Task(description=analysis.name,
                      prompt=analysis.prompt,
                      subagent_type="general-purpose",
                      run_in_background=True)
        task_ids.append(task_id)

    # Collect parallel results
    for task_id in task_ids:
        result = TaskOutput(task_id=task_id)
        process_result(result)

except ToolUnavailableError:
    # Fallback: Run analyses sequentially in main agent
    for analysis in parallel_analyses:
        result = execute_analysis_in_main_agent(analysis)
        process_result(result)
```

**When to use sequential fallback:**
- Task tool temporarily unavailable
- User explicitly requests sequential execution
- Context size constraints prevent parallel handoffs
- Debugging parallel delegation issues

## CLAUDE.md Placement Rules

| Directory Type | Documentation File | Why |
|----------------|-------------------|-----|
| Source dirs (`agents/`, `commands/`, `skills/`) | `CLAUDE.md` | Auto-loads when working here |
| Config dirs (`.claude/agents/`, `.claude/commands/`) | `README.md` | Ignored by parsers |

**Key distinction:**
- **Source directories** contain definitions symlinked globally → use `CLAUDE.md`
- **Config directories** (`.claude/*`) are project overrides → use `README.md` (or no docs)

**For skills specifically:**
- `skills/CLAUDE.md` - Auto-loads when editing skills (THIS FILE)
- Each skill has `SKILL.md` (not CLAUDE.md) as its definition file

## Directory Organization

```
skills/
├── CLAUDE.md                         # This file
├── agent-creator/
├── code-reviewer/
├── critical-thinking/
├── deep-reading-framework/
├── error-debugger/
├── expert-planning/
├── implementation-evaluator/
├── researching-comprehensive/
├── repository-analyzer/
├── skill-creator/
├── systematic-debugging/
├── technical-doc-review/
├── test-driven-development/
└── [other skills...]/
    ├── critiquing-exhaustively/          # Comprehensive technical review
    │   ├── SKILL.md                      # Main skill definition
    │   └── references/                   # Supporting specifications
    │       ├── persona-prompts.md        # Orthogonal persona definitions
    │       ├── ultrathink-prompts.md     # Adversarial reviewer
    │       └── output-format.md          # JSON schema for findings
```

## Advanced Skill Patterns

### Subagent Architecture

Some complex skills use **parallel subagent patterns** for structured analysis:

**Example: critiquing-exhaustively**
- **Main skill**: Orchestrates comprehensive technical review
- **Persona subagents**: Orthogonal reviewers (Devil's Advocate, Gap Finder, antirez, etc.)
- **Structured output**: Agent-executable findings with do_not, expected_after fields

**Key characteristics:**
- Multiple specialized subagents run in parallel
- Standardized output formats enable orchestrator parsing
- Each subagent focuses on specific analysis lens
- Results are synthesized into comprehensive critique

**Implementation pattern:**
```
skills/skill-name/
├── SKILL.md                    # Main orchestrator logic
└── references/
    ├── subagent-format.md      # Output format specification
    └── handoffs/               # Inter-agent contracts
```

**Output format requirements:**
- Machine-parseable structure (markdown with consistent headers)
- Severity levels (P0-P3) for prioritization
- Evidence citations with line numbers
- Category classification for filtering
- Error state handling

This pattern is useful for:
- Complex analysis requiring multiple perspectives
- Large-scale reviews needing structured output
- Quality assurance workflows with specific criteria

## Related Documentation

- `agents/CLAUDE.md`: Agent creation and discovery
- `commands/CLAUDE.md`: Slash command workflows
- `hooks/CLAUDE.md`: Claude Code hooks system
- Root `CLAUDE.md`: Project-wide documentation index

## Skill Discovery Architecture

Claude Code uses a **directory-level symlink** for skill discovery:

```
~/.claude/skills/ → ~/formaltask/skills/
```

This means:
- All skills in `formaltask/skills/` are automatically available
- Each skill's `SKILL.md` is discovered and parsed automatically
- No individual file symlinks needed
- Subdirectories are recursively scanned for `SKILL.md` files

## Hierarchical CLAUDE.md Behavior

This file is **auto-loaded** when Claude Code processes tasks in the `skills/` directory because:

1. **Source Directory**: This is the SOURCE directory (symlinked globally)
2. **Automatic Discovery**: CLAUDE.md in source directories auto-loads
3. **Global Availability**: Content is available everywhere via symlink
4. **Not in .claude/**: Config directory `.claude/skills/` contains NO CLAUDE.md

This hierarchical behavior enables:
- Global skill documentation accessible from any context
- Consistent patterns across agent/command/skills creation
- Clear separation between SOURCE and CONFIG directories
