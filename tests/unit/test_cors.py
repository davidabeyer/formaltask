"""Tests for CORS header configuration."""

from formaltask.api.cors import cors_headers, preflight_headers

# Production and development origins
PROD_ORIGIN = "https://formaltask.com"
DEV_ORIGIN = "http://localhost:3000"
UNKNOWN_ORIGIN = "https://evil.com"


class TestPreflightHeaders:
    """Preflight OPTIONS returns correct headers."""

    def test_preflight_allows_production_origin(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert headers["Access-Control-Allow-Origin"] == PROD_ORIGIN

    def test_preflight_allows_dev_origin(self):
        headers = preflight_headers(DEV_ORIGIN)
        assert headers["Access-Control-Allow-Origin"] == DEV_ORIGIN

    def test_preflight_rejects_unknown_origin(self):
        headers = preflight_headers(UNKNOWN_ORIGIN)
        assert "Access-Control-Allow-Origin" not in headers

    def test_preflight_includes_allowed_methods(self):
        headers = preflight_headers(PROD_ORIGIN)
        methods = headers["Access-Control-Allow-Methods"]
        for method in ("GET", "POST", "PUT", "DELETE", "OPTIONS"):
            assert method in methods

    def test_preflight_includes_allowed_headers(self):
        headers = preflight_headers(PROD_ORIGIN)
        allowed = headers["Access-Control-Allow-Headers"]
        assert "Content-Type" in allowed
        assert "Authorization" in allowed

    def test_preflight_sets_max_age(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert "Access-Control-Max-Age" in headers


class TestCorsHeaders:
    """Regular response CORS headers."""

    def test_cors_allows_production_origin(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/tasks")
        assert headers["Access-Control-Allow-Origin"] == PROD_ORIGIN

    def test_cors_allows_dev_origin(self):
        headers = cors_headers(DEV_ORIGIN, path="/api/tasks")
        assert headers["Access-Control-Allow-Origin"] == DEV_ORIGIN

    def test_cors_rejects_unknown_origin(self):
        headers = cors_headers(UNKNOWN_ORIGIN, path="/api/tasks")
        assert "Access-Control-Allow-Origin" not in headers


class TestCredentialsMode:
    """Credentials mode enabled for auth endpoints."""

    def test_auth_endpoint_enables_credentials(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/auth/login")
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_auth_token_endpoint_enables_credentials(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/auth/token")
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_non_auth_endpoint_no_credentials(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/tasks")
        assert "Access-Control-Allow-Credentials" not in headers

    def test_preflight_auth_enables_credentials(self):
        headers = preflight_headers(PROD_ORIGIN, path="/api/auth/login")
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_preflight_non_auth_no_credentials(self):
        headers = preflight_headers(PROD_ORIGIN, path="/api/tasks")
        assert "Access-Control-Allow-Credentials" not in headers
