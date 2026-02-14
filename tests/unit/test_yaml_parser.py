"""Tests for YAML spec parser - yaml_parser.py.

Tests parse_specs_dir(), verify_decomposition(), validate_task_quality(),
_criteria_to_db_rows(), and related functions for spec directory parsing.
"""

import pytest
from pydantic import ValidationError


class TestSpecSpec:
    """Test SpecSpec model for spec.yaml validation."""

    def test_specspec_valid_with_title(self):
        """SpecSpec accepts valid spec with required title field."""
        from formaltask.epics.models import SpecSpec

        spec = SpecSpec(
            title="Task 1: User Authentication",
            summary="Implement user authentication",
            context="System needs secure login",
            implementation=["Create login form", "Add JWT handling"],
            acceptance_criteria=["Users can log in"],
            testing=["Unit: test_auth.py"],
        )
        assert spec.title == "Task 1: User Authentication"
        assert spec.summary == "Implement user authentication"
        assert len(spec.implementation) == 2

    def test_specspec_accepts_inputs_with_task_ref(self):
        """SpecSpec accepts inputs dict with $task[N].outputs references."""
        from formaltask.epics.models import SpecSpec

        spec = SpecSpec(
            title="test",
            summary="s",
            context="c",
            implementation=["step"],
            acceptance_criteria=["criterion"],
            testing=["test"],
            inputs={"x": "$task[1].outputs.y"},
        )
        assert spec.inputs == {"x": "$task[1].outputs.y"}

    def test_specspec_accepts_outputs_dict(self):
        """SpecSpec accepts outputs dict with file paths."""
        from formaltask.epics.models import SpecSpec

        spec = SpecSpec(
            title="test",
            summary="s",
            context="c",
            implementation=["step"],
            acceptance_criteria=["criterion"],
            testing=["test"],
            outputs={"schema": ".artifacts/schema.json"},
        )
        assert spec.outputs == {"schema": ".artifacts/schema.json"}

    def test_specspec_accepts_prompt_template(self):
        """SpecSpec accepts prompt_template string field."""
        from formaltask.epics.models import SpecSpec

        spec = SpecSpec(
            title="test",
            summary="s",
            context="c",
            implementation=["step"],
            acceptance_criteria=["criterion"],
            testing=["test"],
            prompt_template="You are a {role}",
        )
        assert spec.prompt_template == "You are a {role}"

    def test_specspec_with_all_fields(self):
        """SpecSpec accepts all optional fields."""
        from formaltask.epics.models import SpecSpec

        spec = SpecSpec(
            title="Task 1: Complex Feature",
            summary="Complex feature",
            context="Detailed context",
            implementation=["Step 1", "Step 2"],
            acceptance_criteria=["Criterion 1", "Criterion 2"],
            testing=["Unit: tests"],
            required_reviews=["security"],
            depends_on=[1, 2],
            implements=["g-1", "g-2"],
            skills=["python", "sql"],
        )
        assert spec.required_reviews == ["security"]
        assert spec.depends_on == [1, 2]
        assert spec.implements == ["g-1", "g-2"]
        assert spec.skills == ["python", "sql"]

    def test_specspec_title_required(self):
        """SpecSpec without title field raises ValidationError."""
        from formaltask.epics.models import SpecSpec

        with pytest.raises(ValidationError) as exc_info:
            SpecSpec(
                summary="Summary without title",
                context="Context",
                implementation=["Step 1"],
                acceptance_criteria=["Criterion"],
                testing=["Test"],
            )
        assert "title" in str(exc_info.value).lower()


class TestValidateTaskQuality:
    """Test validate_task_quality function."""

    def test_validate_task_quality_undersized(self):
        """validate_task_quality warns on undersized tasks."""
        from formaltask.epics.yaml_parser import validate_task_quality

        tasks = [
            {
                "title": "Tiny task",
                "description": "Short description",
                "criteria": ["One criterion"],
            }
        ]
        result = validate_task_quality(tasks)
        assert len(result.warnings) > 0
        assert any("undersized" in w.message.lower() for w in result.warnings)


class TestParseSpecsDir:
    """Test parse_specs_dir() function for directory-based spec parsing."""

    def test_parse_specs_dir_output_keys(self, tmp_path):
        """parse_specs_dir() returns dicts with expected keys (golden test).

        Output dict keys: title, description, criteria, depends_on,
        required_reviews, skills, spec_content, documentation_required
        """
        from formaltask.epics.yaml_parser import parse_specs_dir

        # Create spec directory with one spec file
        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        spec_content = """
title: "Task 1: Test Task"
summary: Test task summary
context: Test context
implementation:
  - Step 1
acceptance_criteria:
  - id: c-1
    current: Criterion 1
    command: pytest -k test
    history: []
testing:
  - Unit test
depends_on: []
required_reviews:
  - code-quality
skills:
  - python
"""
        (spec_dir / "task-1-test-spec.yaml").write_text(spec_content)

        # Parse the spec directory
        tasks = parse_specs_dir(str(spec_dir))

        # Verify expected output keys
        assert len(tasks) == 1
        task = tasks[0]
        expected_keys = {
            "title",
            "description",
            "criteria",
            "depends_on",
            "required_reviews",
            "skills",
            "spec_content",
            "documentation_required",
            "inputs",
            "outputs",
            "prompt_template",
        }
        assert set(task.keys()) == expected_keys

        # Verify values are correctly mapped
        assert task["title"] == "Task 1: Test Task"
        assert task["description"] == "Test task summary"
        assert task["spec_content"] == spec_content
        assert task["depends_on"] == []
        assert task["required_reviews"] == ["code-quality"]
        assert task["skills"] == ["python"]

    def test_parse_specs_dir_sorts_by_task_number(self, tmp_path):
        """parse_specs_dir() sorts spec files numerically by task-{N}- prefix.

        Files: task-1-*, task-10-*, task-2-* should sort as: 1, 2, 10
        Not lexicographically: 1, 10, 2
        """
        from formaltask.epics.yaml_parser import parse_specs_dir

        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        # Create spec files with out-of-order numeric prefixes
        for n in [10, 1, 2]:
            spec_content = f"""
title: "Task {n}: Task number {n}"
summary: Task {n} summary
context: Context for task {n}
implementation:
  - Step 1
acceptance_criteria:
  - id: c-{n}
    current: Criterion {n}
    command: pytest -k test{n}
    history: []
testing:
  - Unit test
depends_on: []
required_reviews: []
skills: []
"""
            (spec_dir / f"task-{n}-spec.yaml").write_text(spec_content)

        tasks = parse_specs_dir(str(spec_dir))

        # Verify numeric sort order (1, 2, 10), not lexicographic (1, 10, 2)
        assert len(tasks) == 3
        assert tasks[0]["title"] == "Task 1: Task number 1"
        assert tasks[1]["title"] == "Task 2: Task number 2"
        assert tasks[2]["title"] == "Task 10: Task number 10"

    def test_parse_specs_dir_raises_on_missing_title(self, tmp_path):
        """parse_specs_dir() raises SpecFormatError when spec lacks title."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        # Create spec file without title field
        spec_content = """
summary: Test summary without title
context: Context
implementation:
  - Step 1
acceptance_criteria:
  - id: c-1
    current: Criterion 1
    command: pytest -k test
    history: []
testing:
  - Unit test
depends_on: []
required_reviews: []
skills: []
"""
        (spec_dir / "task-1-spec.yaml").write_text(spec_content)

        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(spec_dir))
        assert "title" in str(exc_info.value).lower()

    def test_parse_specs_dir_validates_self_dependency(self, tmp_path):
        """parse_specs_dir() raises SpecFormatError for self-dependency."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        spec_content = """
title: "Task 1: Self-referencing task"
summary: Task with self-dependency
context: Context
implementation:
  - Step 1
acceptance_criteria:
  - id: c-1
    current: Criterion 1
    command: pytest -k test
    history: []
testing:
  - Unit test
depends_on: [1]
required_reviews: []
skills: []
"""
        (spec_dir / "task-1-spec.yaml").write_text(spec_content)

        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(spec_dir))
        assert "cannot depend on itself" in str(exc_info.value).lower()

    def test_parse_specs_dir_validates_forward_dependency(self, tmp_path):
        """parse_specs_dir() raises SpecFormatError for forward dependency."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        # Task 1 depends on task 2 (forward reference)
        spec_content = """
title: "Task 1: Forward-referencing task"
summary: Task with forward dependency
context: Context
implementation:
  - Step 1
acceptance_criteria:
  - id: c-1
    current: Criterion 1
    command: pytest -k test
    history: []
testing:
  - Unit test
depends_on: [2]
required_reviews: []
skills: []
"""
        (spec_dir / "task-1-spec.yaml").write_text(spec_content)

        # Task 2
        spec_content_2 = """
title: "Task 2: Normal task"
summary: Normal task
context: Context
implementation:
  - Step 1
acceptance_criteria:
  - id: c-2
    current: Criterion 2
    command: pytest -k test
    history: []
testing:
  - Unit test
depends_on: []
required_reviews: []
skills: []
"""
        (spec_dir / "task-2-spec.yaml").write_text(spec_content_2)

        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(spec_dir))
        assert "forward dependency" in str(exc_info.value).lower()


class TestCriteriaToDbRows:
    """Test _criteria_to_db_rows() function directly."""

    def test_criteria_to_db_rows_with_criterionv2(self):
        """_criteria_to_db_rows([CriterionV2(id='c-1', current='t', command='cmd')]) returns [{'text': 't', 'command': 'cmd'}]."""
        from formaltask.epics.models import CriterionV2
        from formaltask.epics.yaml_parser import _criteria_to_db_rows

        criteria = [CriterionV2(id="c-1", current="t", command="cmd", history=[])]
        result = _criteria_to_db_rows(criteria)
        assert result == [{"text": "t", "command": "cmd"}]

    def test_criteria_to_db_rows_with_multiple_criteria(self):
        """_criteria_to_db_rows converts multiple CriterionV2 entries."""
        from formaltask.epics.models import CriterionV2
        from formaltask.epics.yaml_parser import _criteria_to_db_rows

        criteria = [
            CriterionV2(id="c-1", current="First criterion", command="pytest -k first", history=[]),
            CriterionV2(
                id="c-2", current="Second criterion", command="pytest -k second", history=[]
            ),
        ]
        result = _criteria_to_db_rows(criteria)
        assert result == [
            {"text": "First criterion", "command": "pytest -k first"},
            {"text": "Second criterion", "command": "pytest -k second"},
        ]

    def test_criteria_to_db_rows_with_string_criteria(self):
        """_criteria_to_db_rows converts plain strings to dicts with empty command."""
        from formaltask.epics.yaml_parser import _criteria_to_db_rows

        criteria = ["Plain string criterion", "Another string"]
        result = _criteria_to_db_rows(criteria)
        assert result == [
            {"text": "Plain string criterion", "command": ""},
            {"text": "Another string", "command": ""},
        ]

    def test_criteria_to_db_rows_with_mixed_criteria(self):
        """_criteria_to_db_rows handles mixed string and CriterionV2."""
        from formaltask.epics.models import CriterionV2
        from formaltask.epics.yaml_parser import _criteria_to_db_rows

        criteria = [
            "String criterion",
            CriterionV2(
                id="c-1", current="CriterionV2 criterion", command="pytest -k test", history=[]
            ),
        ]
        result = _criteria_to_db_rows(criteria)
        assert result == [
            {"text": "String criterion", "command": ""},
            {"text": "CriterionV2 criterion", "command": "pytest -k test"},
        ]


class TestTaskRefPattern:
    """Test TASK_REF_PATTERN for $task[N].outputs.key extraction."""

    def test_task_ref_pattern_exists(self):
        """TASK_REF_PATTERN can be imported from yaml_parser."""
        from formaltask.epics.yaml_parser import TASK_REF_PATTERN

        assert TASK_REF_PATTERN is not None

    def test_task_ref_pattern_extracts_task_number_and_output_key(self):
        """TASK_REF_PATTERN extracts (task_number, output_key) from $task[N].outputs.key."""
        from formaltask.epics.yaml_parser import TASK_REF_PATTERN

        match = TASK_REF_PATTERN.search("$task[1].outputs.schema_file")
        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "schema_file"

    def test_task_ref_pattern_finds_all_refs_in_string(self):
        """TASK_REF_PATTERN.findall() finds multiple refs."""
        from formaltask.epics.yaml_parser import TASK_REF_PATTERN

        text = "Use $task[1].outputs.x and $task[2].outputs.y together"
        matches = TASK_REF_PATTERN.findall(text)
        assert matches == [("1", "x"), ("2", "y")]


class TestAutoDependencyInference:
    """Test auto-dependency inference from $task[N].outputs references in inputs."""

    def test_auto_dep_infers_dependency_from_input_ref(self, tmp_path):
        """parse_specs_dir infers dependency when inputs has $task[N].outputs ref."""
        from formaltask.epics.yaml_parser import parse_specs_dir

        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        # Task 1 - no dependencies
        (spec_dir / "task-1-base.yaml").write_text("""
title: "Task 1: Base"
summary: Base task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
outputs:
  schema: ".artifacts/schema.json"
""")

        # Task 2 - references task 1's output (should auto-infer dep)
        (spec_dir / "task-2-consumer.yaml").write_text("""
title: "Task 2: Consumer"
summary: Consumer task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
inputs:
  schema: "$task[1].outputs.schema"
""")

        tasks = parse_specs_dir(str(spec_dir))

        assert len(tasks) == 2
        # Task 2 (index 1) should have dependency on task 1 (0-indexed: 0)
        assert 0 in tasks[1]["depends_on"]

    def test_auto_dep_merges_with_explicit_depends_on(self, tmp_path):
        """Auto-inferred deps are merged with explicit depends_on."""
        from formaltask.epics.yaml_parser import parse_specs_dir

        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        # Tasks 1 and 2
        for n in [1, 2]:
            (spec_dir / f"task-{n}-base.yaml").write_text(f"""
title: "Task {n}: Base"
summary: Base task {n}
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
outputs:
  out{n}: ".artifacts/out{n}.json"
""")

        # Task 3 - explicit dep on task 1, input ref to task 2
        (spec_dir / "task-3-consumer.yaml").write_text("""
title: "Task 3: Consumer"
summary: Consumer task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: [1]
required_reviews: []
inputs:
  data: "$task[2].outputs.out2"
""")

        tasks = parse_specs_dir(str(spec_dir))

        assert len(tasks) == 3
        # Task 3 should depend on both task 1 (explicit) and task 2 (auto)
        # 0-indexed: task 1 = 0, task 2 = 1
        assert 0 in tasks[2]["depends_on"]
        assert 1 in tasks[2]["depends_on"]

    def test_auto_dep_rejects_forward_reference_in_input(self, tmp_path):
        """parse_specs_dir rejects forward ref in inputs (task 1 refs task 2)."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        # Task 1 - forward reference to task 2
        (spec_dir / "task-1-bad.yaml").write_text("""
title: "Task 1: Bad"
summary: Bad task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
inputs:
  data: "$task[2].outputs.future_data"
""")

        # Task 2
        (spec_dir / "task-2-target.yaml").write_text("""
title: "Task 2: Target"
summary: Target task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
outputs:
  future_data: ".artifacts/data.json"
""")

        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(spec_dir))
        assert "forward" in str(exc_info.value).lower()

    def test_auto_dep_rejects_task_zero_reference(self, tmp_path):
        """parse_specs_dir rejects $task[0].outputs reference (1-indexed, so 0 is invalid)."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        (spec_dir / "task-1-bad.yaml").write_text("""
title: "Task 1: Bad"
summary: Bad task
context: Context
implementation: [Step]
acceptance_criteria: [Criterion]
testing: [Test]
depends_on: []
required_reviews: []
inputs:
  data: "$task[0].outputs.invalid"
""")

        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(spec_dir))
        assert (
            "out-of-bounds" in str(exc_info.value).lower()
            or "invalid" in str(exc_info.value).lower()
        )


class TestSpecFormatError:
    """Test SpecFormatError replaces EpicFormatError."""

    def test_specformaterror_exists(self):
        """SpecFormatError can be imported from yaml_parser."""
        from formaltask.epics.yaml_parser import SpecFormatError

        assert SpecFormatError is not None

    def test_specformaterror_raised_on_invalid_spec(self, tmp_path):
        """SpecFormatError is raised for invalid spec files."""
        from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

        spec_dir = tmp_path / "test-specs"
        spec_dir.mkdir()

        # Invalid YAML content
        (spec_dir / "task-1-spec.yaml").write_text("invalid: yaml: content:")

        with pytest.raises(SpecFormatError):
            parse_specs_dir(str(spec_dir))
