"""Small helpers for timestamps returned by external services."""

from datetime import datetime, timezone


def is_after_utc(value: str, threshold: datetime) -> bool:
    """Compare an ISO timestamp after normalizing both values to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc) > threshold
    except (AttributeError, TypeError, ValueError):
        return False
