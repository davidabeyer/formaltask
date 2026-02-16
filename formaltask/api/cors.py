"""CORS header configuration for production and development origins."""

import posixpath

ALLOWED_ORIGINS = {
    "https://formaltask.com",
    "http://localhost:3000",
}

ALLOWED_METHODS = "GET, POST, PUT, DELETE, OPTIONS"
ALLOWED_HEADERS = "Content-Type, Authorization"
MAX_AGE = "86400"


def _is_auth_path(path: str) -> bool:
    """Check if path is an auth endpoint, normalizing to prevent traversal."""
    normalized = posixpath.normpath(path)
    return normalized == "/api/auth" or normalized.startswith("/api/auth/")


def preflight_headers(origin: str, path: str = "/") -> dict[str, str]:
    """Build CORS headers for an OPTIONS preflight request."""
    if origin not in ALLOWED_ORIGINS:
        return {}

    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Allow-Headers": ALLOWED_HEADERS,
        "Access-Control-Max-Age": MAX_AGE,
        "Vary": "Origin",
    }

    if _is_auth_path(path):
        headers["Access-Control-Allow-Credentials"] = "true"

    return headers


def cors_headers(origin: str, path: str = "/") -> dict[str, str]:
    """Build CORS headers for a regular response."""
    if origin not in ALLOWED_ORIGINS:
        return {}

    headers = {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }

    if _is_auth_path(path):
        headers["Access-Control-Allow-Credentials"] = "true"

    return headers
