---
consumes: [codebase-context, project-paths]
produces: [db-tasks]
optional: true
---
# Phase 2: SPECS_TO_TASKS

Run `ft epic decompose {project} {spec_dir}` for final DB commit.

**EXIT CRITERIA:** Tasks created in DB.
