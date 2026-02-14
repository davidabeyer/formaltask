Feature: Task Workflow Management

  Scenario: Create a task in an epic
    Given a clean FormalTask database
    And an epic named "test-epic" exists
    When I create a task "My Task" in "test-epic"
    Then the task "My Task" should exist in "test-epic"

  Scenario: Start a task
    Given a clean FormalTask database
    And an epic named "work-epic" exists
    And a task "Work Task" exists in "work-epic"
    When I start the task "Work Task"
    Then the task "Work Task" should have status "in_progress"

  Scenario: Complete a task
    Given a clean FormalTask database
    And an epic named "done-epic" exists
    And a started task "Done Task" exists in "done-epic"
    When I complete the task "Done Task"
    Then the task "Done Task" should have status "completed"

  Scenario: Retrieve task by ID
    Given a clean FormalTask database
    And an epic named "lookup-epic" exists
    And a task "Lookup Task" exists in "lookup-epic"
    When I retrieve task "Lookup Task" by ID
    Then the task should have title "Lookup Task"
    And the task should have epic "lookup-epic"

  Scenario: Tasks are assigned positions
    Given a clean FormalTask database
    And an epic named "ordered-epic" exists
    And a task "First Task" exists in "ordered-epic"
    And a task "Second Task" exists in "ordered-epic"
    When I retrieve task "First Task" by ID
    Then the task should have position 1
    When I retrieve task "Second Task" by ID
    Then the task should have position 2
