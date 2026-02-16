"""Tests for CORS header configuration."""

from formaltask.api.cors import cors_headers, preflight_headers

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

    def test_preflight_allowed_methods(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE, OPTIONS"

    def test_preflight_allowed_headers(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert headers["Access-Control-Allow-Headers"] == "Content-Type, Authorization"

    def test_preflight_sets_max_age(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert headers["Access-Control-Max-Age"] == "86400"

    def test_preflight_includes_vary_origin(self):
        headers = preflight_headers(PROD_ORIGIN)
        assert headers["Vary"] == "Origin"


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

    def test_cors_includes_vary_origin(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/tasks")
        assert headers["Vary"] == "Origin"


class TestCredentialsMode:
    """Credentials mode enabled for auth endpoints."""

    def test_auth_login_enables_credentials(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/auth/login")
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_auth_token_enables_credentials(self):
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

    def test_path_traversal_does_not_bypass_auth_check(self):
        headers = cors_headers(PROD_ORIGIN, path="/api/auth/../tasks")
        assert "Access-Control-Allow-Credentials" not in headers
