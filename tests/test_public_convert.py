"""Checks for the conversion API that does not require an account."""
import asyncio
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as converter_app  # noqa: E402
import conversion_jobs  # noqa: E402
import public_convert  # noqa: E402


class _Request:
    """Small stand-in for the headers the gateway forwards."""

    def __init__(self, forwarded=None, host=None):
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}
        self.client = type("Client", (), {"host": host})() if host else None


@pytest.fixture(autouse=True)
def clear_public_limits():
    public_convert._recent_jobs.clear()
    yield
    public_convert._recent_jobs.clear()


def test_public_limit_uses_the_forwarded_client_address():
    """The first forwarded address is the caller, not the gateway."""
    request = _Request(forwarded="203.0.113.8, 10.0.0.2")
    assert public_convert.client_address(request) == "203.0.113.8"
    assert public_convert.client_address(_Request(host="127.0.0.1")) == "127.0.0.1"

    for _ in range(public_convert.PUBLIC_JOBS_PER_HOUR):
        public_convert.allow_address("203.0.113.8", now=1_000.0)
    with pytest.raises(HTTPException) as error:
        public_convert.allow_address("203.0.113.8", now=1_000.0)
    assert error.value.status_code == 429
    # A different address still has its own allowance.
    public_convert.allow_address("203.0.113.9", now=1_000.0)


def test_public_download_ignores_signed_in_jobs(monkeypatch, tmp_path):
    """A normal library conversion must not be readable from the public route."""
    monkeypatch.setattr(converter_app, "OUTPUT_FOLDER", str(tmp_path))
    conversion_id = str(uuid.uuid4())
    output_dir = tmp_path / conversion_id
    output_dir.mkdir()
    (output_dir / f"{conversion_id}.epub").write_bytes(b"epub")
    (output_dir / "status.json").write_text(
        json.dumps({"output_filename": f"{conversion_id}.epub"}),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(converter_app.download_without_account(conversion_id))
    assert error.value.status_code == 404


def test_public_status_points_at_the_public_download(monkeypatch, tmp_path):
    """Completed public jobs advertise the no-login download links."""
    monkeypatch.setattr(converter_app, "OUTPUT_FOLDER", str(tmp_path))
    monkeypatch.setenv("PUBLIC_API_URL", "https://example.test")
    conversion_id = str(uuid.uuid4())
    output_dir = tmp_path / conversion_id
    output_dir.mkdir()
    (output_dir / "status.json").write_text(
        json.dumps(
            {
                "public": True,
                "status": "completed",
                "tables_download_url": "https://old.example/tables",
                "archive_download_url": "https://old.example/archive",
            }
        ),
        encoding="utf-8",
    )

    payload = asyncio.run(converter_app.public_conversion_status(conversion_id))
    assert payload.download_url == (
        f"https://example.test/api/public/download/{conversion_id}?kind=primary"
    )
    assert payload.tables_download_url.endswith("?kind=tables")
    assert payload.archive_download_url.endswith("?kind=archive")


def test_anonymous_conversion_is_not_saved_to_the_library(monkeypatch):
    """No account means there is no library row to write."""
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("library request should not be sent")

    monkeypatch.setattr(conversion_jobs.httpx, "Client", fail_if_called)
    assert conversion_jobs._save_to_library(
        "book.pdf", 10, 1, 1, "https://files.example/book.epub",
        "job", {}, "", "en",
    ) is None
