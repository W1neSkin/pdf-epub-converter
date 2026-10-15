"""Public conversion helpers.

These calls do not require an account. The same free-plan file limits still
apply in the converter. A small per-address cap keeps the free server from
being filled by anonymous uploads.
"""
import os
import time
from typing import Dict, Optional

from fastapi import HTTPException, Request

# Enough for a person or an agent to try the API. Not a bulk service.
PUBLIC_JOBS_PER_HOUR = 8
PUBLIC_WINDOW_SECONDS = 60 * 60
_recent_jobs: Dict[str, list] = {}


def client_address(request: Request) -> str:
    """Prefer the original client when the gateway forwards the request."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def allow_address(address: str, now: Optional[float] = None) -> None:
    """Count one new public conversion for this address."""
    moment = time.time() if now is None else now
    # Drop addresses that have been quiet for the whole window.
    stale = [
        key for key, stamps in _recent_jobs.items()
        if stamps and moment - stamps[-1] >= PUBLIC_WINDOW_SECONDS
    ]
    for key in stale:
        _recent_jobs.pop(key, None)

    recent = [
        stamp for stamp in _recent_jobs.get(address, [])
        if moment - stamp < PUBLIC_WINDOW_SECONDS
    ]
    if len(recent) >= PUBLIC_JOBS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Public conversion limit reached. Try again in an hour.",
        )
    recent.append(moment)
    _recent_jobs[address] = recent


def allow_public_job(request: Request) -> None:
    """Count one new public conversion for the calling address."""
    allow_address(client_address(request))


def public_api_base() -> str:
    """Base URL clients should use for status and downloads."""
    return os.getenv(
        "PUBLIC_API_URL",
        "https://pdf-converter-api-gateway.onrender.com",
    ).rstrip("/")


def public_download_url(conversion_id: str, kind: str = "primary") -> str:
    """Download link that does not ask for a login."""
    return f"{public_api_base()}/api/public/download/{conversion_id}?kind={kind}"
