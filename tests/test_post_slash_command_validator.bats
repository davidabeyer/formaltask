#!/usr/bin/env bats

setup() {
  HOOK_SCRIPT="$HOME/.claude/hooks/post-slash-command-validator.sh"
  TEST_DIR="$(mktemp -d)"
  cd "$TEST_DIR"
  git init
}

teardown() {
  # Remove worktrees if any
  cd "$TEST_DIR" 2>/dev/null || true
  git worktree list 2>/dev/null | grep -v "(bare)" | tail -n +2 | awk '{print $1}' | xargs -r -n1 git worktree remove --force 2>/dev/null || true
  rm -rf "$TEST_DIR"
}

@test "hook allows non-pm commands" {
  run bash -c "echo '{\"command\": \"/start-session\"}' | $HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "allowed" ]]
  [[ "$output" =~ "true" ]]
}

@test "hook validates epic-sync worktree creation" {
  # Setup: Create epic structure but NO worktree
  mkdir -p .claude/epics/test-epic

  run bash -c "echo '{\"command\": \"/pm-epic-sync test-epic\"}' | $HOOK_SCRIPT"

  # Should fail - worktree missing
  [ "$status" -eq 0 ]
  [[ "$output" =~ "allowed" ]]
  [[ "$output" =~ "false" ]]
  [[ "$output" =~ "worktree" ]]
}

@test "hook validates epic-sync github-mapping creation" {
  # Setup: Create worktree but NO github-mapping.md
  mkdir -p .claude/epics/test-epic2
  git worktree add worktrees/epic-test-epic2 -b epic/test-epic2

  run bash -c "echo '{\"command\": \"/pm-epic-sync test-epic2\"}' | $HOOK_SCRIPT"

  # Should fail - github-mapping.md missing
  [ "$status" -eq 0 ]
  [[ "$output" =~ "allowed" ]]
  [[ "$output" =~ "false" ]]
  [[ "$output" =~ "github-mapping" ]]
}

@test "hook passes when all validations succeed" {
  # Setup: Create both worktree and github-mapping.md
  mkdir -p .claude/epics/test-epic3
  git worktree add worktrees/epic-test-epic3 -b epic/test-epic3
  touch .claude/epics/test-epic3/github-mapping.md

  run bash -c "echo '{\"command\": \"/pm-epic-sync test-epic3\"}' | $HOOK_SCRIPT"

  # Should pass
  [ "$status" -eq 0 ]
  [[ "$output" =~ "allowed" ]]
  [[ "$output" =~ "true" ]]
}
