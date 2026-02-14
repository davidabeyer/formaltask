#!/usr/bin/env python3
"""
Pytest Configuration for Integration Tests

Shared fixtures for integration test scenarios.
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from tests.fixtures.paths import LIB_DIR


@pytest.fixture
def git_repo(tmp_path):
    """Create a temp git repo with one commit.

    Eliminates ~15 lines of repeated setup in git integration tests.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path

# Add lib directory for shared utilities (Task #2128)
sys.path.insert(0, str(LIB_DIR))


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temporary Memory directory structure"""
    memory_dir = tmp_path / "Memory"
    sessions_dir = memory_dir / "sessions"
    sessions_dir.mkdir(parents=True)
    daily_notes_dir = memory_dir / "Daily Notes"
    daily_notes_dir.mkdir(parents=True)
    return memory_dir


@pytest.fixture
def temp_claude_dir(tmp_path):
    """Create temporary .claude directory structure"""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "tmp").mkdir()
    (claude_dir / "workflow-worker" / "logs").mkdir(parents=True)
    return claude_dir


@pytest.fixture
def sample_transcript_50_turns():
    """Generate sample 50-turn JSONL transcript"""
    turns = []
    for i in range(50):
        turn = {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Turn {i + 1} content with discussion about implementation",
            "timestamp": f"2025-11-11T{i // 10:02d}:{i % 10:02d}:00Z",
        }
        turns.append(json.dumps(turn))
    return "\n".join(turns) + "\n"


@pytest.fixture
def sample_transcript_30_turns():
    """Generate sample 30-turn JSONL transcript"""
    turns = []
    for i in range(30):
        turn = {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Turn {i + 1} - working on feature implementation",
            "timestamp": f"2025-11-11T00:{i:02d}:00Z",
        }
        turns.append(json.dumps(turn))
    return "\n".join(turns) + "\n"


@pytest.fixture
def mock_sonnet_narrative_response():
    """Mock Sonnet API response for narrative generation"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = json.dumps(
        {
            "narrative": [
                {"content": "User requested authentication implementation", "label": "requirement"},
                {
                    "content": "Discussed JWT vs session-based approach, chose JWT for stateless API",
                    "label": "decision",
                },
                {
                    "content": "Implemented JWT token generation with bcrypt password hashing",
                    "label": "implementation",
                },
                {
                    "content": "Created comprehensive test suite with 95% coverage",
                    "label": "testing",
                },
            ]
        }
    )
    return mock_response


@pytest.fixture
def mock_sonnet_summary_response():
    """Mock Sonnet API response for summary generation"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = json.dumps(
        {
            "summary": "Session focused on implementing authentication using JWT tokens. "
            "Key decisions included choosing JWT over sessions for stateless API design. "
            "Implementation completed with comprehensive test coverage (95%) including "
            "password hashing with bcrypt and rate limiting protection."
        }
    )
    return mock_response


@pytest.fixture
def mock_sonnet_handoff_response():
    """Mock Sonnet API response for handoff generation"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = json.dumps(
        {
            "current_task": "Implementing authentication endpoint with JWT tokens",
            "recent_turns": [
                "User requested login endpoint implementation",
                "Discussed validation requirements for email and password",
                "Implemented password hashing with bcrypt",
                "Added rate limiting (5 attempts per minute)",
                "Created integration tests for auth flow",
            ],
            "files_changed": [
                {"path": "api/auth.py", "status": "added"},
                {"path": "api/middleware.py", "status": "modified"},
                {"path": "tests/test_auth.py", "status": "added"},
            ],
            "decisions": [
                "Using bcrypt for password hashing (industry standard)",
                "Rate limit: 5 login attempts per minute per IP",
                "JWT expiry: 24 hours for access tokens",
            ],
            "questions": [
                "Should we add 2FA support in this phase?",
                "Do we need refresh tokens or is 24h sufficient?",
            ],
            "next_steps": [
                "Add password reset endpoint",
                "Implement email verification flow",
                "Add refresh token mechanism",
            ],
            "important_context": [
                "User preference: Simple over complex solutions",
                "Security is highest priority",
                "Performance target: <100ms for auth check",
            ],
        }
    )
    return mock_response


@pytest.fixture
def sample_meta_file_content():
    """Sample META.md file content"""
    return """---
topic: authentication
created: 2025-11-10
updated: 2025-11-10
---

# Authentication Epic - Session META

## Session Timeline

### 2025-11-10 - Session 1
Initial planning and architecture design.

## Current State

Planning complete, ready for implementation.
"""


@pytest.fixture
def sample_daily_note_content():
    """Sample Daily Note content"""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"""---
date: {today}
---

# Daily Note - {today}

## Sessions

"""


# =============================================================================
# Event-Driven Flow Fixtures (Task #1223)
# =============================================================================


@pytest.fixture
def event_flow_transcript():
    """Realistic transcript for event-driven flow integration tests.

    Simulates a development session with:
    - Implementation discussion
    - Decision making
    - Error encountered and fixed
    - Test writing
    """
    turns = [
        {
            "type": "human",
            "message": {
                "content": "I need to implement a user authentication system using JWT tokens."
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": "I'll help you implement JWT authentication. Let me first check what auth libraries you have. Looking at your package.json, I see you're using Express. I recommend using jsonwebtoken for JWT handling and bcrypt for password hashing."
            },
        },
        {
            "type": "human",
            "message": {"content": "Sounds good. Let's start with the login endpoint."},
        },
        {
            "type": "assistant",
            "message": {
                "content": "I'll create the login endpoint. First, let me implement the password validation and JWT token generation.\n\nDecision: Using bcrypt with cost factor 12 for password hashing - this provides good security without excessive computation time."
            },
        },
        {
            "type": "human",
            "message": {
                "content": "I'm getting an error: TypeError: Cannot read property 'password' of undefined"
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": "The error occurs because the request body isn't being parsed. Let me add the express.json() middleware to fix this.\n\nSolution: Added express.json() middleware before the auth routes - this parses incoming JSON request bodies."
            },
        },
        {
            "type": "human",
            "message": {
                "content": "That fixed it. Now let's add rate limiting to prevent brute force attacks."
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": "Good security practice. I'll implement rate limiting.\n\nDecision: Rate limit of 5 login attempts per minute per IP address. This balances security with user experience."
            },
        },
        {"type": "human", "message": {"content": "Can you write tests for the auth flow?"}},
        {
            "type": "assistant",
            "message": {
                "content": "I'll create comprehensive tests for the authentication flow including:\n1. Successful login returns JWT token\n2. Invalid credentials return 401\n3. Rate limiting blocks after 5 attempts\n4. Token validation works correctly"
            },
        },
        {
            "type": "human",
            "message": {"content": "The tests are passing. What about token expiration?"},
        },
        {
            "type": "assistant",
            "message": {
                "content": "Decision: JWT tokens expire after 24 hours. For sensitive operations, we could add refresh tokens later, but 24h is sufficient for now.\n\nLesson learned: Always set token expiration - never use non-expiring tokens in production."
            },
        },
    ]
    return "\n".join(json.dumps(turn) for turn in turns) + "\n"


@pytest.fixture
def event_flow_expected_narrative():
    """Expected narrative structure for event-driven flow tests.

    Represents a quality 2-3 sentence narrative summarizing session work.
    """
    return (
        "This session implemented JWT authentication with bcrypt password hashing and rate limiting. "
        "Key decisions included using bcrypt cost factor 12 for security-performance balance "
        "and limiting login attempts to 5 per minute per IP to prevent brute force attacks. "
        "Comprehensive test coverage was added for the authentication flow."
    )
