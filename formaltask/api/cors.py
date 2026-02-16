"""CORS header configuration for production and development origins."""

ALLOWED_ORIGINS = {
    "https://formaltask.com",
    "http://localhost:3000",
}

ALLOWED_METHODS = "GET, POST, PUT, DELETE, OPTIONS"
ALLOWED_HEADERS = "Content-Type, Authorization"
MAX_AGE = "86400"


def preflight_headers(origin: str, path: str = "/") -> dict[str, str]:
    """Build CORS headers for an OPTIONS preflight request."""
    if origin not in ALLOWED_ORIGINS:
        return {}

    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Allow-Headers": ALLOWED_HEADERS,
        "Access-Control-Max-Age": MAX_AGE,
    }

    if path.startswith("/api/auth/"):
        headers["Access-Control-Allow-Credentials"] = "true"

    return headers


def cors_headers(origin: str, path: str = "/") -> dict[str, str]:
    """Build CORS headers for a regular response."""
    if origin not in ALLOWED_ORIGINS:
        return {}

    headers = {
        "Access-Control-Allow-Origin": origin,
    }

    if path.startswith("/api/auth/"):
        headers["Access-Control-Allow-Credentials"] = "true"

    return headers
