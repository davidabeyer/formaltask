Feature: Epic Workflow Management

  Scenario: Create a new epic
    Given a clean FormalTask database
    When I create an epic named "test-epic"
    Then the epic "test-epic" should exist

  Scenario: Creating duplicate epic fails
    Given a clean FormalTask database
    And an epic named "existing-epic" exists
    When I try to create an epic named "existing-epic"
    Then I should get a duplicate error

  Scenario: List all epics
    Given a clean FormalTask database
    And an epic named "epic-one" exists
    And an epic named "epic-two" exists
    When I list all epics
    Then I should see 2 epics in the result

  Scenario: Get epic status with no tasks
    Given a clean FormalTask database
    And an epic named "empty-epic" exists
    When I get the status of "empty-epic"
    Then the status should show 0 total tasks

  Scenario: Get epic status with mixed task states
    Given a clean FormalTask database
    And an epic named "mixed-epic" exists
    And a task "Task 1" in "mixed-epic" with status "completed"
    And a task "Task 2" in "mixed-epic" with status "in_progress"
    And a task "Task 3" in "mixed-epic" with status "open"
    When I get the status of "mixed-epic"
    Then the status should show 3 total tasks
    And the status should show 1 completed tasks
