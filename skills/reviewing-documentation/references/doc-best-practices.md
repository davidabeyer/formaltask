# Technical Documentation Best Practices

## Completeness Checklist

### Essential Sections

**Getting Started / Quickstart**
- Installation instructions for all supported platforms
- Minimal working example (copy-paste ready)
- Prerequisites clearly listed with versions
- Expected output shown
- Time to first success < 5 minutes

**Core Concepts**
- Key terminology defined upfront
- Mental models and analogies
- Architecture overview with diagrams
- When to use (and when NOT to use)

**API Reference**
- Every public method/function/endpoint documented
- Parameters: type, required/optional, default values
- Return values: type and structure
- Error conditions and exception types
- Code examples for each API element

**Examples & Tutorials**
- Real-world use cases (not just "hello world")
- Progressive complexity (beginner → advanced)
- Complete, runnable examples
- Expected output included
- Common pitfalls highlighted

**Configuration**
- All configuration options documented
- Default values stated
- Environment variable alternatives
- Configuration file examples
- Validation rules explained

**Troubleshooting**
- Common errors with solutions
- Debug mode instructions
- How to file bug reports
- Known limitations
- FAQ section

**Version Information**
- Current version clearly stated
- Changelog or release notes
- Breaking changes highlighted
- Migration guides between major versions
- Deprecation warnings with timelines

## Quality Criteria

### Clarity
- **One concept per paragraph**
- **Active voice** ("Run the command" not "The command should be run")
- **Concrete examples** before abstractions
- **Technical terms defined** on first use
- **Consistent terminology** throughout

### Code Examples
- **Self-contained** (copy-paste runnable)
- **Syntax highlighted** with language tags
- **Output shown** when relevant
- **Error handling** included
- **Realistic scenarios** not toy examples
- **Commented** for non-obvious parts

### Structure
- **Logical flow**: Installation → Quick start → Concepts → Reference → Advanced
- **Searchable**: Good headings, keywords, index
- **Scannable**: Lists, tables, code blocks break up prose
- **Linked**: Cross-references between related topics
- **Hierarchical**: Clear heading levels (H1 → H2 → H3)

### Accuracy
- **Version-specific**: State which version docs apply to
- **Tested**: Examples actually work as written
- **Up-to-date**: No outdated screenshots, deprecated APIs
- **Precise**: No vague phrases like "usually" or "might"

### Developer Experience

**Time to value**
- 5 minutes to first working example
- 15 minutes to understand core concepts
- 30 minutes to build something real

**Error messages**
- Errors documented in troubleshooting
- Links from error messages to docs
- Clear remediation steps

**Discoverability**
- Search functionality
- Table of contents
- Breadcrumbs for navigation
- Related topics suggested
- Tags/categories for filtering

## Common Documentation Anti-Patterns

### The Missing Middle
- ✅ Good: Quickstart + Complete API reference
- ❌ Bad: Quickstart jumps to advanced, no middle ground
- **Fix**: Add tutorials bridging gap between basics and reference

### The Assumptive Docs
- ❌ "Simply configure the X" (assumes knowledge of X)
- ❌ "Just use Y" (what is Y? where is it?)
- ❌ "Obviously, you need Z" (not obvious to newcomers)
- **Fix**: Define prerequisites, link to background reading

### The "It's in the Code" Fallacy
- ❌ "See the source for details"
- ❌ "Refer to the implementation"
- **Fix**: Document behavior, not just implementation

### The Orphaned Example
- ❌ Code snippets without context
- ❌ No explanation of what code does or why
- **Fix**: Explain before showing, show output

### The Stale Docs
- ❌ Screenshots of old UI
- ❌ Examples using deprecated APIs
- ❌ No version information
- **Fix**: CI checks, version tags, update schedule

### The Wall of Text
- ❌ Giant paragraphs with no breaks
- ❌ No code examples, diagrams, or visuals
- ❌ Everything in prose
- **Fix**: Use lists, tables, diagrams, code blocks

### The Vague Warning
- ❌ "Be careful with this feature"
- ❌ "This may cause issues"
- ❌ "Use at your own risk"
- **Fix**: Specify exact risks, conditions, and alternatives

## Documentation Types

### API Documentation
- **Endpoint**: URL, HTTP method
- **Authentication**: Required credentials/tokens
- **Request**: Headers, parameters, body schema
- **Response**: Status codes, body schema, examples
- **Errors**: All possible error codes with meanings
- **Rate limits**: Quotas, throttling behavior
- **Versioning**: API version in URL or header

### Library/SDK Documentation
- **Installation**: Package managers, manual install
- **Initialization**: Required setup, configuration
- **Classes/Modules**: Purpose, when to use
- **Methods**: Signatures, parameters, return types
- **Exceptions**: What can throw, when, why
- **Threading**: Thread-safety guarantees
- **Examples**: Common patterns, best practices

### CLI Documentation
- **Commands**: All subcommands listed
- **Flags/Options**: Long and short forms
- **Arguments**: Positional vs optional
- **Exit codes**: What each code means
- **Examples**: Common workflows
- **Configuration**: Config files, env vars
- **Shell completion**: Installation instructions

### Configuration Documentation
- **Format**: YAML/JSON/TOML structure
- **Options**: Every field documented
- **Types**: Expected data types
- **Validation**: Rules and constraints
- **Defaults**: What happens if omitted
- **Examples**: Complete working configs
- **Schema**: JSON schema or equivalent

## Accessibility Standards

**Readability**
- Flesch reading ease score > 60
- Sentences < 25 words average
- Paragraphs < 5 sentences
- Grade level: 8th-10th grade for general docs

**Inclusivity**
- Gender-neutral language
- No idioms or cultural references
- Define acronyms on first use
- Provide text alternatives for images
- Keyboard navigation documented

**Localization-friendly**
- Avoid culture-specific examples
- Use ISO date formats
- Specify units (metric preferred)
- Separable UI screenshots/text

## Review Checklist

Use this checklist when reviewing technical documentation:

**Structure (30 points)**
- [ ] Clear hierarchy of headings (5 pts)
- [ ] Logical flow from basic to advanced (5 pts)
- [ ] Table of contents for long docs (5 pts)
- [ ] Searchable/scannable layout (5 pts)
- [ ] Cross-links between related topics (5 pts)
- [ ] Version clearly indicated (5 pts)

**Completeness (30 points)**
- [ ] Getting started guide present (5 pts)
- [ ] Installation for all platforms (5 pts)
- [ ] Core concepts explained (5 pts)
- [ ] Complete API reference (5 pts)
- [ ] Troubleshooting section (5 pts)
- [ ] Examples for common use cases (5 pts)

**Quality (30 points)**
- [ ] Code examples are runnable (10 pts)
- [ ] Active voice, clear language (5 pts)
- [ ] Technical terms defined (5 pts)
- [ ] Error cases documented (5 pts)
- [ ] No broken links (5 pts)

**Developer Experience (10 points)**
- [ ] < 5 min to first success (5 pts)
- [ ] Real-world examples (not toy) (3 pts)
- [ ] Migration guides if breaking changes (2 pts)

**Scoring:**
- 90-100: Excellent
- 75-89: Good
- 60-74: Acceptable (needs improvement)
- < 60: Poor (requires significant work)

## Common Review Findings

**High Priority (Fix immediately)**
- Missing getting started guide
- No installation instructions
- Code examples don't run
- Breaking changes undocumented
- Security issues not called out

**Medium Priority (Fix soon)**
- Incomplete API reference
- Missing error documentation
- No troubleshooting section
- Inconsistent terminology
- Outdated examples

**Low Priority (Nice to have)**
- More real-world examples
- Better diagrams
- Video tutorials
- Interactive demos
- PDF export option

## Documentation Maturity Model

**Level 1: Minimal**
- README with basic usage
- Installation instructions
- Some code examples

**Level 2: Functional**
- + Complete API reference
- + Getting started guide
- + Troubleshooting section

**Level 3: Professional**
- + Tutorials for common use cases
- + Architecture documentation
- + Migration guides
- + Searchable

**Level 4: Excellent**
- + Interactive examples
- + Video walkthroughs
- + Community contributions
- + Multi-language support
- + Auto-generated from code

**Level 5: World-class**
- + Personalized onboarding
- + AI-powered search
- + Live examples in browser
- + Analytics-driven improvements
- + Version-specific docs
