import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.datetime_utils import is_after_utc  # noqa: E402


def test_library_timestamp_comparison_accepts_utc_and_legacy_naive_values():
    """Old and new Supabase timestamps must not break library statistics."""
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert is_after_utc("2026-01-02T00:00:00+00:00", cutoff)
    assert is_after_utc("2026-01-02T00:00:00", cutoff)
    assert not is_after_utc("2025-12-31T23:59:59Z", cutoff)
    assert not is_after_utc("invalid", cutoff)
