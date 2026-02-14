---
consumes: [verified-docs]
produces: [published-docs]
---
# Phase 7: Final Output

Apply verified documentation to actual files.

## Logic

```python
# Read verification results
verification = Read(f"{run.run_dir}/06-verification.md")

# If all verified, apply
if all_accurate(verification):
    # Write or update the actual documentation files
    Write(target_readme, final_readme_content)
    Write(target_claudemd, final_claudemd_content)
else:
    # Fix inaccuracies first
    # Return to Phase 5 with corrections
```
