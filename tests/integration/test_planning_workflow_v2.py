"""Integration tests for CriterionV2 planning workflow.

Task #2844: Verifies end-to-end planning workflow with new inline annotation format:
1. /plan creates plan.yaml with CriterionV2 goals
2. /critique appends findings to goal history inline
3. /revise sets resolution on findings
4. /decompose creates specs with implements: backlinks
5. Validator blocks malformed writes at each step

Tests:
- E2E: test_full_planning_workflow_new_format
- E2E: test_validator_blocks_in_workflow
"""

import yaml

from formaltask.epics.models import CriterionV2, HistoryEntry
from formaltask.validators.planning_schema_validator import check


class TestFullPlanningWorkflowNewFormat:
    """E2E test for plan/critique/revise/decompose with CriterionV2."""

    def test_plan_creates_criterionv2_goals(self):
        """Plan file should contain CriterionV2 goals with id, current, command, history."""
        # Simulate /plan output with CriterionV2 format
        plan_content = """
schema_version: 1
name: test-project
original_goal: |
  Add user authentication

requirements:
  problem: "Users cannot log in"
  goals:
    - id: "g-1"
      current: "Users can log in with email/password"
      command: "pytest tests/test_auth.py::test_login -v"
      history: []
    - id: "g-2"
      current: "Login attempts are rate-limited"
      command: "pytest tests/test_auth.py::test_rate_limit -v"
      history: []
  scope:
    in:
      - Authentication endpoint
    out:
      - OAuth integration

provenance:
  status: "draft"
"""
        data = yaml.safe_load(plan_content)

        # Verify goals are CriterionV2 format
        goals = data["requirements"]["goals"]
        assert len(goals) == 2

        # Each goal has id, current, command, history
        for goal in goals:
            assert "id" in goal
            assert "current" in goal
            assert "command" in goal
            assert "history" in goal
            # Validate with Pydantic model
            CriterionV2.model_validate(goal)

    def test_critique_appends_to_goal_history(self):
        """After /critique, goals should have findings in history (not separate .md)."""
        # Plan with history after critique appended findings inline
        plan_with_critique = """
schema_version: 1
name: test-project

requirements:
  problem: "Users cannot log in"
  goals:
    - id: "g-1"
      current: "Users can log in with email/password"
      history:
        - version: "r1"
          text: "Users can log in with email/password"
          critique:
            verdict: "FIX_AND_SHIP"
            findings:
              - priority: "P1"
                finding: "Missing password complexity requirement"
                action: "Add minimum 8 chars, 1 uppercase rule"
    - id: "g-2"
      current: "Login attempts are rate-limited"
      history: []
"""
        data = yaml.safe_load(plan_with_critique)
        goals = data["requirements"]["goals"]

        # First goal should have history entry with critique
        goal_1 = goals[0]
        assert len(goal_1["history"]) == 1
        history_entry = goal_1["history"][0]
        assert history_entry["version"] == "r1"
        assert "critique" in history_entry
        assert history_entry["critique"]["verdict"] == "FIX_AND_SHIP"
        assert history_entry["critique"]["findings"][0]["priority"] == "P1"

        # Validate history entry structure
        HistoryEntry.model_validate(history_entry)

    def test_revise_sets_resolution_on_findings(self):
        """After /revise, findings should have resolution set."""
        # Plan after revision with resolution on each finding
        plan_with_resolution = """
schema_version: 1
name: test-project

requirements:
  problem: "Users cannot log in"
  goals:
    - id: "g-1"
      current: "Users can log in with email/password (8+ chars, 1 uppercase)"
      history:
        - version: "r1"
          text: "Users can log in with email/password"
          critique:
            verdict: "FIX_AND_SHIP"
            findings:
              - priority: "P1"
                finding: "Missing password complexity requirement"
                action: "Add minimum 8 chars, 1 uppercase rule"
                resolution: "fixed"
"""
        data = yaml.safe_load(plan_with_resolution)
        goals = data["requirements"]["goals"]

        # Finding should have resolution
        goal_1 = goals[0]
        history_entry = goal_1["history"][0]
        finding = history_entry["critique"]["findings"][0]
        assert finding["resolution"] == "fixed"

        # Validate with Pydantic model
        HistoryEntry.model_validate(history_entry)

    def test_decompose_creates_specs_with_implements_backlinks(self):
        """Specs created by /decompose should have implements: field with goal references."""
        # Spec file content after decompose
        spec_content = """
summary: "Implement login endpoint"
context: |
  Users need to authenticate with email/password.
implementation:
  - Add login endpoint to auth router
  - Validate password complexity
acceptance_criteria:
  - id: "c-1"
    current: "Login endpoint returns JWT on success"
    command: "pytest tests/test_auth.py::test_login_returns_jwt -v"
    history: []
testing:
  - Unit test for login validation
  - Integration test for auth flow
implements:
  - "g-1"
  - "g-2"
"""
        data = yaml.safe_load(spec_content)

        # Spec should have implements field
        assert "implements" in data
        assert data["implements"] == ["g-1", "g-2"]

        # Acceptance criteria should be CriterionV2
        criteria = data["acceptance_criteria"]
        assert len(criteria) == 1
        CriterionV2.model_validate(criteria[0])

    def test_full_workflow_completes_without_validation_errors(self):
        """Complete workflow: plan → critique → revise → decompose."""
        # Phase 1: /plan creates plan with CriterionV2 goals
        plan_content = """
name: auth-feature
description: User authentication
tasks:
  - title: Implement login
    summary: Add login endpoint
    acceptance_criteria:
      - id: "c-1"
        current: "Login works with valid credentials"
        command: "pytest tests/test_auth.py::test_login -v"
        history: []
    implements:
      - "g-1"
"""
        # Validate plan write
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/auth-plan.yaml",
                "content": plan_content,
            },
        }
        result = check(ctx)
        assert result is None, f"Plan write blocked: {result}"

        # Phase 2: /critique appends to history (simulated in plan)
        plan_after_critique = """
name: auth-feature
description: User authentication
tasks:
  - title: Implement login
    summary: Add login endpoint
    acceptance_criteria:
      - id: "c-1"
        current: "Login works with valid credentials"
        command: "pytest tests/test_auth.py::test_login -v"
        history:
          - version: "r1"
            text: "Login works with valid credentials"
            critique:
              verdict: "FIX_AND_SHIP"
              findings:
                - priority: "P1"
                  finding: "Missing rate limiting"
                  action: "Add rate limiting to endpoint"
"""
        ctx["tool_input"]["content"] = plan_after_critique
        result = check(ctx)
        assert result is None, f"Plan with critique blocked: {result}"

        # Phase 3: /revise sets resolution on findings
        plan_after_revise = """
name: auth-feature
description: User authentication
tasks:
  - title: Implement login
    summary: Add login endpoint with rate limiting
    acceptance_criteria:
      - id: "c-1"
        current: "Login works with valid credentials and rate limiting"
        command: "pytest tests/test_auth.py::test_login_rate_limited -v"
        history:
          - version: "r1"
            text: "Login works with valid credentials"
            critique:
              verdict: "FIX_AND_SHIP"
              findings:
                - priority: "P1"
                  finding: "Missing rate limiting"
                  action: "Add rate limiting to endpoint"
                  resolution: "fixed"
"""
        ctx["tool_input"]["content"] = plan_after_revise
        result = check(ctx)
        assert result is None, f"Plan with resolution blocked: {result}"

        # Phase 4: /decompose creates spec
        spec_content = """
summary: "Implement login endpoint"
context: |
  Add login with rate limiting.
implementation:
  - Add login endpoint
acceptance_criteria:
  - id: "c-1"
    current: "Login works with rate limiting"
    command: "pytest tests/test_auth.py::test_login_rate_limited -v"
    history: []
testing:
  - Integration test
implements:
  - "g-1"
"""
        spec_ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/specs/login-spec.yaml",
                "content": spec_content,
            },
        }
        result = check(spec_ctx)
        assert result is None, f"Spec write blocked: {result}"


class TestValidatorBlocksInWorkflow:
    """Test validator blocks malformed YAML at each workflow step."""

    def test_validator_blocks_plan_missing_id(self):
        """Validator should block /plan write with CriterionV2 missing id field."""
        # Invalid: CriterionV2 dict missing required 'id' field
        invalid_plan = """
name: test
description: Test
tasks:
  - title: Test task
    summary: Test summary
    acceptance_criteria:
      - current: "Some criterion"
        command: "pytest -k test"
        history: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": invalid_plan,
            },
        }
        result = check(ctx)
        assert result is not None
        assert result["decision"] == "block"
        assert "id" in result["reason"].lower()

    def test_validator_blocks_spec_invalid_criterionv2(self):
        """Validator should block /decompose spec with invalid CriterionV2 id pattern."""
        # Invalid: id doesn't match c-{N} or g-{N} pattern
        invalid_spec = """
summary: "Test spec"
context: "Test context"
implementation:
  - Step 1
acceptance_criteria:
  - id: "invalid-id"
    current: "Some criterion"
    command: "pytest -k test"
testing:
  - Test 1
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/specs/test-spec.yaml",
                "content": invalid_spec,
            },
        }
        result = check(ctx)
        assert result is not None
        assert result["decision"] == "block"
        assert "pattern" in result["reason"].lower() or "id" in result["reason"].lower()

    def test_validator_allows_valid_criterionv2_at_each_step(self):
        """Validator should allow valid CriterionV2 writes at each workflow step."""
        # Valid plan file
        valid_plan = """
name: test
description: Test
tasks:
  - title: Test task
    summary: Test summary
    acceptance_criteria:
      - id: "c-1"
        current: "Valid criterion"
        command: "pytest -k test"
        history: []
"""
        plan_ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": valid_plan,
            },
        }
        assert check(plan_ctx) is None

        # Valid epic file
        valid_epic = """
name: test-epic
description: Test epic
tasks:
  - title: Task 1
    summary: Summary 1
    acceptance_criteria:
      - id: "g-1"
        current: "Goal 1"
        command: "pytest -k goal"
        history: []
"""
        epic_ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/epics/test/epic.yaml",
                "content": valid_epic,
            },
        }
        assert check(epic_ctx) is None

        # Valid spec file
        valid_spec = """
summary: "Test spec"
context: "Context"
implementation:
  - Step
acceptance_criteria:
  - id: "c-1"
    current: "Criterion"
    command: "pytest -k criterion"
testing:
  - Test
"""
        spec_ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/specs/task-spec.yaml",
                "content": valid_spec,
            },
        }
        assert check(spec_ctx) is None

    def test_no_separate_md_critique_files_created(self):
        """Critique findings should be inline in plan.yaml, not in separate .md files."""
        # This test verifies the skill contract by checking that after critique,
        # the plan.yaml contains history entries with CritiqueResult
        plan_after_critique = """
schema_version: 1
name: test-project

requirements:
  goals:
    - id: "g-1"
      current: "Feature X works"
      history:
        - version: "r1"
          text: "Feature X works"
          critique:
            verdict: "REVISE"
            findings:
              - priority: "P0"
                finding: "Missing error handling"
                action: "Add try/catch around external calls"
"""
        data = yaml.safe_load(plan_after_critique)

        # Critique data is inline in goal history
        goal = data["requirements"]["goals"][0]
        assert len(goal["history"]) > 0
        assert "critique" in goal["history"][0]
        assert goal["history"][0]["critique"]["verdict"] == "REVISE"

        # The skill should NOT create separate files like:
        # - critique-round1.md
        # - findings.md
        # All critique data goes inline in plan.yaml


class TestRoundTripYAML:
    """Test YAML round-trip: parse → serialize → parse → compare."""

    def test_round_trip_preserves_critique_data(self):
        """YAML round-trip preserves all CritiqueResult data."""
        original_yaml = """
schema_version: 1
name: round-trip-test

requirements:
  goals:
    - id: "g-1"
      current: "Feature works"
      history:
        - version: "r1"
          text: "Feature works"
          critique:
            verdict: "FIX_AND_SHIP"
            findings:
              - priority: "P0"
                finding: "Critical issue with unicode: 日本語 🎉"
                action: "Fix with special chars: <>&\\""
                resolution: "fixed"
              - priority: "P1"
                finding: "Minor issue"
                action: "Consider later"
"""
        # Parse original
        data1 = yaml.safe_load(original_yaml)

        # Serialize back to YAML
        serialized = yaml.dump(data1, default_flow_style=False, allow_unicode=True)

        # Parse again
        data2 = yaml.safe_load(serialized)

        # Compare
        goal1_orig = data1["requirements"]["goals"][0]
        goal1_rt = data2["requirements"]["goals"][0]

        assert goal1_orig["id"] == goal1_rt["id"]
        assert goal1_orig["current"] == goal1_rt["current"]

        # History preserved
        assert len(goal1_orig["history"]) == len(goal1_rt["history"])

        # Critique preserved
        critique_orig = goal1_orig["history"][0]["critique"]
        critique_rt = goal1_rt["history"][0]["critique"]
        assert critique_orig["verdict"] == critique_rt["verdict"]
        assert len(critique_orig["findings"]) == len(critique_rt["findings"])

        # Findings preserved including unicode
        f0_orig = critique_orig["findings"][0]
        f0_rt = critique_rt["findings"][0]
        assert f0_orig["priority"] == f0_rt["priority"]
        assert f0_orig["finding"] == f0_rt["finding"]
        assert f0_orig["action"] == f0_rt["action"]
        assert f0_orig["resolution"] == f0_rt["resolution"]

    def test_round_trip_validates_with_pydantic(self):
        """Round-tripped data validates with Pydantic models."""
        original_yaml = """
history:
  - version: "r1"
    text: "Original text"
    critique:
      verdict: "APPROVED"
      findings: []
  - version: "r2"
    text: "Updated text"
    critique:
      verdict: "FIX_AND_SHIP"
      findings:
        - priority: "P1"
          finding: "Issue found"
          action: "Fix it"
"""
        data = yaml.safe_load(original_yaml)
        serialized = yaml.dump(data)
        data_rt = yaml.safe_load(serialized)

        # Validate each history entry
        for entry in data_rt["history"]:
            HistoryEntry.model_validate(entry)


class TestMultiRoundHistory:
    """Test multiple critique rounds accumulating history."""

    def test_three_round_critique_cycle(self):
        """Three rounds of critique accumulate in history correctly."""
        # Round 1: Initial critique
        round1_yaml = """
requirements:
  goals:
    - id: "g-1"
      current: "Feature X works"
      history:
        - version: "r1"
          text: "Feature X works"
          critique:
            verdict: "REVISE"
            findings:
              - priority: "P0"
                finding: "Missing error handling"
                action: "Add try/except"
"""
        data = yaml.safe_load(round1_yaml)
        goal = data["requirements"]["goals"][0]

        assert len(goal["history"]) == 1
        assert goal["history"][0]["critique"]["verdict"] == "REVISE"

        # Round 2: After revision, new critique
        goal["history"][0]["critique"]["findings"][0]["resolution"] = "fixed"
        goal["history"].append({
            "version": "r2",
            "text": "Feature X works with error handling",
            "critique": {
                "verdict": "FIX_AND_SHIP",
                "findings": [
                    {"priority": "P1", "finding": "Missing logging", "action": "Add logging"}
                ]
            }
        })

        assert len(goal["history"]) == 2
        assert goal["history"][0]["critique"]["findings"][0]["resolution"] == "fixed"
        assert goal["history"][1]["critique"]["verdict"] == "FIX_AND_SHIP"

        # Round 3: Final approval
        goal["history"][1]["critique"]["findings"][0]["resolution"] = "fixed"
        goal["history"].append({
            "version": "r3",
            "text": "Feature X works with error handling and logging",
            "critique": {
                "verdict": "APPROVED",
                "findings": []
            }
        })

        assert len(goal["history"]) == 3
        assert goal["history"][2]["critique"]["verdict"] == "APPROVED"

        # Validate all entries
        for entry in goal["history"]:
            HistoryEntry.model_validate(entry)

    def test_multiple_goals_independent_history(self):
        """Each goal accumulates history independently."""
        plan_yaml = """
requirements:
  goals:
    - id: "g-1"
      current: "Goal 1 current"
      command: "pytest -k goal1"
      history:
        - version: "r1"
          text: "Goal 1 original"
          critique:
            verdict: "APPROVED"
            findings: []
    - id: "g-2"
      current: "Goal 2 revised"
      command: "pytest -k goal2"
      history:
        - version: "r1"
          text: "Goal 2 original"
          critique:
            verdict: "FIX_AND_SHIP"
            findings:
              - priority: "P1"
                finding: "Needs work"
                action: "Fix"
        - version: "r2"
          text: "Goal 2 revised"
          critique:
            verdict: "APPROVED"
            findings: []
"""
        data = yaml.safe_load(plan_yaml)
        goals = data["requirements"]["goals"]

        # Goal 1 has 1 history entry
        assert len(goals[0]["history"]) == 1

        # Goal 2 has 2 history entries
        assert len(goals[1]["history"]) == 2

        # Each validates independently
        for goal in goals:
            CriterionV2.model_validate(goal)


class TestResolutionUpdates:
    """Test /revise resolution update scenarios."""

    def test_update_resolution_on_specific_finding(self):
        """Resolution can be set on specific findings independently."""
        plan_yaml = """
history:
  - version: "r1"
    text: "Original"
    critique:
      verdict: "REVISE"
      findings:
        - priority: "P0"
          finding: "Critical 1"
          action: "Fix 1"
        - priority: "P0"
          finding: "Critical 2"
          action: "Fix 2"
        - priority: "P1"
          finding: "Important"
          action: "Fix 3"
"""
        data = yaml.safe_load(plan_yaml)
        findings = data["history"][0]["critique"]["findings"]

        # Simulate /revise updating specific resolutions
        findings[0]["resolution"] = "fixed"
        findings[1]["resolution"] = "rejected"  # Critique was wrong
        findings[2]["resolution"] = "deferred"  # Will fix later

        # Validate
        entry = HistoryEntry.model_validate(data["history"][0])
        assert entry.critique is not None
        assert entry.critique.findings[0].resolution == "fixed"
        assert entry.critique.findings[1].resolution == "rejected"
        assert entry.critique.findings[2].resolution == "deferred"

    def test_partial_resolution_valid(self):
        """Some findings can have resolution while others don't."""
        plan_yaml = """
history:
  - version: "r1"
    text: "Text"
    critique:
      verdict: "FIX_AND_SHIP"
      findings:
        - priority: "P0"
          finding: "Fixed"
          action: "Done"
          resolution: "fixed"
        - priority: "P1"
          finding: "Pending"
          action: "TODO"
"""
        data = yaml.safe_load(plan_yaml)
        entry = HistoryEntry.model_validate(data["history"][0])

        assert entry.critique is not None
        assert entry.critique.findings[0].resolution == "fixed"
        assert entry.critique.findings[1].resolution is None


