# antirez on Deleting Code

Core principles from Salvatore Sanfilippo (antirez), creator of Redis.

---

## The Deletion Philosophy

antirez is famous for aggressive code deletion. Redis stays maintainable because code that doesn't earn its place gets deleted.

> "The best code is no code at all. Every new line of code you willingly bring into the world is code that has to be debugged, code that has to be read and understood, code that has to be supported."

---

## Key Principles for Dead Code

### Complexity is the Enemy

Every line of code is a liability:
- It can have bugs
- It must be maintained
- It must be understood
- It costs cognitive load

Dead code has all the costs with zero benefits.

### The 80/20 Rule of Deletion

Most features (and most code) don't matter:
- 20% of code does 80% of the work
- The other 80% is candidates for deletion
- Dead code is 0% of the work, 100% liability

### Write Code to Delete It

Good code is written knowing it might be deleted:
- Clear boundaries
- Minimal dependencies
- Obvious purpose

Code that's hard to delete was probably over-engineered.

---

## antirez Code Review Questions

When reviewing code for deletion:

| Question | Dead if... |
|----------|------------|
| Does it run in production? | Never executes |
| Does it have callers? | Zero callers |
| Would I write this today? | No |
| Does the test suite cover it? | Not tested |
| When was it last modified? | Years ago |
| Does anyone understand it? | No one knows |

---

## The Redis Way

Redis maintains quality through aggressive simplification:

1. **Features get deleted** - If a feature isn't used, it's removed
2. **Code paths get simplified** - Conditional complexity gets flattened
3. **Comments explain why, not what** - Self-documenting code, no comment rot
4. **One way to do things** - Multiple paths to same result = dead code candidates

---

## Quotes Applied

> "Code is a liability, not an asset."

Dead code is pure liability. Delete it.

> "Programming is not about typing, it's about thinking."

The thinking that went into dead code already paid off (or didn't). The code itself is now just bytes.

> "I'm a huge fan of removing code. It's one of my favorite activities."

Channel this energy. Every line deleted is a line that can't confuse future you.

---

## Practical antirez-Style Deletion

### Before deleting, verify:

```bash
# Search entire codebase
grep -rn "function_name" --include="*.py"

# Check git history
git log -p --all -S "function_name" -- "*.py"

# Check if exported
grep -rn "__all__.*function_name"
```

### After verifying it's dead:

```bash
# Delete it
# Don't comment it out
# Don't add a TODO
# Just delete it
```

### The antirez test:

> "Would antirez mass delete this?"

If the answer is "yes", delete it.

---

## Common Excuses (and Rebuttals)

| Excuse | Rebuttal |
|--------|----------|
| "I might need it later" | Git remembers. You won't need it. |
| "It documents what we tried" | Git history documents that better. |
| "Someone might be using it" | Grep proves no one is. |
| "It's not hurting anything" | It's hurting comprehension. |
| "I'll clean it up later" | Later is never. Delete now. |

---

## The Ultimate Rule

> "When in doubt, delete it out."

If you're unsure whether code is dead:
1. Verify it has no callers
2. Verify it's not dynamically invoked
3. Delete it
4. If something breaks, git revert

The fear of deletion creates code graveyards. Be fearless.
