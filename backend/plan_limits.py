"""
Plan limits for PDF conversion.

Free stays small so one Render instance can handle it.
Paid plans can raise pages and file size later, when subscription
money pays for a larger host (more CPU and RAM).
"""

PLANS = {
    "free": {
        "max_pages": 50,
        "max_file_mb": 50,
    },
    # Not sold yet. Numbers are a placeholder for a future paid tier.
    "pro": {
        "max_pages": 2000,
        "max_file_mb": 200,
    },
}


def limits_for(tier: str = "free") -> dict:
    """Return page and size limits for a subscription tier."""
    return PLANS.get(tier or "free", PLANS["free"])
