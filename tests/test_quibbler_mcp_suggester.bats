#!/usr/bin/env bats
# Tests for quibbler_mcp_suggester.py hook

HOOK_SCRIPT="$HOME/.claude/hooks/quibbler_mcp_suggester.py"

@test "suggests MCP review for Write tool on .py file" {
    input='{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.py"}}'
    run bash -c "echo '$input' | python3 '$HOOK_SCRIPT' 2>&1"

    [ "$status" -eq 0 ]
    [[ "$output" == *"mcp__quibbler__review_code"* ]]
}

@test "suggests MCP review for Edit tool on .py file" {
    input='{"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test.py"}}'
    run bash -c "echo '$input' | python3 '$HOOK_SCRIPT' 2>&1"

    [ "$status" -eq 0 ]
    [[ "$output" == *"mcp__quibbler__review_code"* ]]
}

@test "skips suggestion for markdown files" {
    input='{"tool_name": "Write", "tool_input": {"file_path": "/tmp/README.md"}}'
    run bash -c "echo '$input' | python3 '$HOOK_SCRIPT' 2>&1"

    [ "$status" -eq 0 ]
    [[ "$output" != *"mcp__quibbler__review_code"* ]]
}

@test "suggests MCP review for morph-mcp edit_file tool" {
    input='{"tool_name": "mcp__morph-mcp__edit_file", "tool_input": {"path": "/tmp/test.py"}}'
    run bash -c "echo '$input' | python3 '$HOOK_SCRIPT' 2>&1"

    [ "$status" -eq 0 ]
    [[ "$output" == *"mcp__quibbler__review_code"* ]]
}

@test "suggests MCP review for TypeScript files" {
    input='{"tool_name": "Write", "tool_input": {"file_path": "/tmp/app.ts"}}'
    run bash -c "echo '$input' | python3 '$HOOK_SCRIPT' 2>&1"

    [ "$status" -eq 0 ]
    [[ "$output" == *"mcp__quibbler__review_code"* ]]
}
