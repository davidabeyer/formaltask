---
consumes: [raw-findings]
produces: [verified-findings]
optional: true
---
# Adversarial Verification

Challenge findings before reporting. Every finding gets attacked.

For each finding:

1. **Devil's Advocate**: Argue why this finding is WRONG
   - Is the evidence actually conclusive?
   - Could there be a valid reason this exists?

2. **False Positive Check**: Run the actual command
   ```python
   Grep(pattern=finding_pattern, path=project_root, output_mode="content")
   ```

3. **Severity Challenge**: Is this really the right priority?
   - P0 claim → would production break? Prove it.
   - P1 claim → is there actually a real bug? Show the scenario.
   - P2 claim → does anyone care? Name the user impact.

4. **Verdict**:
   | Result | Action |
   |--------|--------|
   | Survives challenge | Keep at stated severity |
   | Partially wrong | Downgrade severity |
   | Completely wrong | Drop it |

Attack your own findings harder than someone else's. "It looks wrong" is not evidence — run the command.