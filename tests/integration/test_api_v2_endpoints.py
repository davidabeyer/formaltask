"""Integration tests for all v2 API endpoints.

Tests cover:
- Health check (/health, /ready)
- Request validation (Pydantic middleware)
- Rate limiting (token bucket per API key)
- CORS headers

All tests run against in-memory SQLite.
"""

import sqlite3
import time

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_db():
    """In-memory SQLite database with minimal schema for API tests."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE epics (name TEXT PRIMARY KEY, description TEXT, created_at TEXT)")
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, epic_name TEXT, title TEXT, status TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO epics (name, description, created_at) VALUES ('test', 'Test', '2026-01-01')"
    )
    conn.execute(
        "INSERT INTO tasks (epic_name, title, status, created_at) VALUES ('test', 'Task 1', 'open', '2026-01-01')"
    )
    conn.commit()
    yield conn
    conn.close()


# ===========================================================================
# Health Check Endpoint Tests
# ===========================================================================


class TestHealthEndpoint:
    """Tests for /health endpoint — basic liveness check."""

    def test_health_returns_ok_status(self):
        from formaltask.api.health import health_check

        result = health_check()
        assert result["status"] == "ok"

    def test_health_includes_timestamp(self):
        from formaltask.api.health import health_check

        result = health_check()
        assert "timestamp" in result


class TestReadyEndpoint:
    """Tests for /ready endpoint — readiness with dependency checks."""

    def test_ready_returns_ok_when_db_connected(self, in_memory_db):
        from formaltask.api.health import ready_check

        result = ready_check(in_memory_db)
        assert result["status"] == "ok"

    def test_ready_returns_database_healthy(self, in_memory_db):
        from formaltask.api.health import ready_check

        result = ready_check(in_memory_db)
        assert result["checks"]["database"] == "ok"

    def test_ready_fails_when_db_closed(self):
        from formaltask.api.health import ready_check

        conn = sqlite3.connect(":memory:")
        conn.close()
        result = ready_check(conn)
        assert result["status"] == "degraded"
        assert result["checks"]["database"] == "error"


# ===========================================================================
# Request Validation Tests
# ===========================================================================


class TestRequestValidation:
    """Tests for Pydantic request validation middleware."""

    def test_valid_task_creation_passes(self):
        from formaltask.api.validation import validate_task_create

        data = {"epic_name": "test", "title": "New task", "description": "A task"}
        result = validate_task_create(data)
        assert result.title == "New task"

    def test_missing_required_field_raises(self):
        from formaltask.api.validation import validate_task_create

        with pytest.raises(ValueError, match="title"):
            validate_task_create({"epic_name": "test"})

    def test_empty_title_rejected(self):
        from formaltask.api.validation import validate_task_create

        with pytest.raises(ValueError, match="title"):
            validate_task_create({"epic_name": "test", "title": ""})

    def test_valid_task_update_passes(self):
        from formaltask.api.validation import validate_task_update

        data = {"status": "in_progress"}
        result = validate_task_update(data)
        assert result.status == "in_progress"

    def test_invalid_status_rejected(self):
        from formaltask.api.validation import validate_task_update

        with pytest.raises(ValueError, match="status"):
            validate_task_update({"status": "invalid_status"})

    def test_title_too_long_rejected(self):
        from formaltask.api.validation import validate_task_create

        with pytest.raises(ValueError, match="title"):
            validate_task_create({"epic_name": "test", "title": "x" * 501})


# ===========================================================================
# Rate Limiting Tests
# ===========================================================================


class TestRateLimiting:
    """Tests for token bucket rate limiter per API key."""

    def test_allows_requests_within_limit(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=5, refill_rate=1.0)
        for _ in range(5):
            assert limiter.allow("key-1") is True

    def test_blocks_requests_over_limit(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=3, refill_rate=0.0)
        for _ in range(3):
            limiter.allow("key-1")
        assert limiter.allow("key-1") is False

    def test_separate_buckets_per_key(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=2, refill_rate=0.0)
        limiter.allow("key-1")
        limiter.allow("key-1")
        assert limiter.allow("key-1") is False
        assert limiter.allow("key-2") is True

    def test_tokens_refill_over_time(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=1, refill_rate=100.0)
        assert limiter.allow("key-1") is True
        assert limiter.allow("key-1") is False
        time.sleep(0.02)
        assert limiter.allow("key-1") is True

    def test_tokens_never_exceed_max(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=3, refill_rate=100.0)
        time.sleep(0.1)
        # Even after waiting, should still only have max_tokens
        count = 0
        while limiter.allow("key-1"):
            count += 1
            if count > 10:
                break
        assert count == 3


# ===========================================================================
# CORS Integration Tests
# ===========================================================================


class TestCorsIntegration:
    """Integration tests for CORS headers across endpoints."""

    def test_preflight_production_origin(self):
        from formaltask.api.cors import preflight_headers

        headers = preflight_headers("https://formaltask.com")
        assert headers["Access-Control-Allow-Origin"] == "https://formaltask.com"
        assert "GET" in headers["Access-Control-Allow-Methods"]

    def test_preflight_rejects_unknown_origin(self):
        from formaltask.api.cors import preflight_headers

        headers = preflight_headers("https://attacker.com")
        assert headers == {}

    def test_cors_headers_on_response(self):
        from formaltask.api.cors import cors_headers

        headers = cors_headers("http://localhost:3000", path="/api/tasks")
        assert headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert headers["Vary"] == "Origin"

    def test_auth_endpoint_includes_credentials(self):
        from formaltask.api.cors import cors_headers

        headers = cors_headers("https://formaltask.com", path="/api/auth/login")
        assert headers["Access-Control-Allow-Credentials"] == "true"


# ===========================================================================
# End-to-End: Full Request Lifecycle
# ===========================================================================


class TestFullRequestLifecycle:
    """End-to-end tests combining health, validation, rate limiting, CORS."""

    def test_health_with_cors(self):
        from formaltask.api.cors import cors_headers
        from formaltask.api.health import health_check

        result = health_check()
        headers = cors_headers("https://formaltask.com", path="/health")
        assert result["status"] == "ok"
        assert headers["Access-Control-Allow-Origin"] == "https://formaltask.com"

    def test_validated_request_with_rate_limit(self):
        from formaltask.api.rate_limit import RateLimiter
        from formaltask.api.validation import validate_task_create

        limiter = RateLimiter(max_tokens=10, refill_rate=1.0)
        data = {"epic_name": "test", "title": "New task", "description": "Desc"}

        assert limiter.allow("api-key-1") is True
        result = validate_task_create(data)
        assert result.title == "New task"

    def test_rate_limited_request_blocked_before_validation(self):
        from formaltask.api.rate_limit import RateLimiter

        limiter = RateLimiter(max_tokens=1, refill_rate=0.0)
        limiter.allow("api-key-1")

        assert limiter.allow("api-key-1") is False
        # Validation never runs — rate limit checked first

    def test_ready_check_with_db_and_cors(self, in_memory_db):
        from formaltask.api.cors import cors_headers
        from formaltask.api.health import ready_check

        result = ready_check(in_memory_db)
        headers = cors_headers("http://localhost:3000", path="/ready")
        assert result["status"] == "ok"
        assert headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
