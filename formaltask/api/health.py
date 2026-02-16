"""Health check endpoints for API v2."""

from datetime import UTC, datetime


def health_check() -> dict:
    """Liveness check — always returns ok if the process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


def ready_check(db_conn) -> dict:
    """Readiness check — verifies database connectivity."""
    checks = {}
    try:
        db_conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
