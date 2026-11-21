"""Health routes for the converter and the gateway's dependency probe.

The gateway used to call ``{SERVICE_URL}/health`` and only fall back to ``/``
on an exact 404. A trailing slash, or a 429/502 while Render woke the
converter, was reported as unhealthy with no status code.
"""
import asyncio
import importlib.util
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as converter_app  # noqa: E402


def _load_gateway():
    """Load the gateway under its own module name so it does not replace ``app``."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    path = ROOT / "services" / "api-gateway" / "app.py"
    spec = importlib.util.spec_from_file_location("api_gateway_app", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["api_gateway_app"] = module
    spec.loader.exec_module(module)
    return module


gateway = _load_gateway()


def _probe(url, handler):
    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await gateway.probe_service(url, client=client)

    return asyncio.run(run())


def test_converter_root_and_health_both_report_healthy():
    """Render probes ``/``. The gateway probes ``/health``. Both must succeed."""
    client = TestClient(converter_app.app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "healthy"
    assert root.json()["service"] == "PDF to EPUB Converter API"

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["service_name"] == "converter-service"
    assert body["status"] == "healthy"
    assert body["version"] == "1.0.0"
    assert body["database_connected"] is True
    assert body["dependencies"] == {"uploads": "ready", "outputs": "ready"}
    assert body["timestamp"]


def test_converter_health_degraded_when_upload_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(converter_app, "UPLOAD_FOLDER", str(tmp_path / "missing"))
    body = TestClient(converter_app.app).get("/health").json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["uploads"] == "missing"
    assert body["dependencies"]["outputs"] == "ready"


def test_normalize_service_base_url_strips_trailing_slash():
    assert gateway.normalize_service_base_url("https://converter.example/") == "https://converter.example"
    assert gateway.normalize_service_base_url("  https://converter.example///  ") == "https://converter.example"


def test_missing_health_route_falls_back_to_root():
    """An older converter only answers `/`. A 404 is the missing-route signal."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(404)
        return httpx.Response(200, json={"status": "healthy"})

    status = _probe("https://converter.example/", handler)
    assert status == "healthy"
    assert seen == ["/health", "/"]


def test_429_does_not_probe_the_other_path():
    """A Cloudflare 429 is this caller being limited. A second GET keeps it going."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(429, headers={"cf-mitigated": "challenge"})

    status = _probe("https://converter.example/", handler)
    assert status == "unhealthy:GET /health HTTP 429 cloudflare-challenge"
    assert seen == ["/health"]


def test_probe_reports_both_status_codes_when_fallback_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(502)
        return httpx.Response(503)

    status = _probe("https://converter.example", handler)
    assert status == "unhealthy:GET /health HTTP 502; GET / HTTP 503"


def test_probe_reports_exception_type_and_still_tries_root():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            raise httpx.TimeoutException("timed out")
        return httpx.Response(200)

    assert _probe("https://converter.example", handler) == "healthy"

    def both_fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    status = _probe("https://converter.example", both_fail)
    assert status == "unavailable:GET /health ConnectError; GET / ConnectError"


def test_probe_stops_after_healthy_health_path():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200)

    assert _probe("https://converter.example", handler) == "healthy"
    assert seen == ["/health"]


def test_missing_service_url_is_unavailable_without_a_request():
    assert asyncio.run(gateway.probe_service("  ")) == "unavailable:MissingServiceUrl"


def test_gateway_health_stays_degraded_and_names_the_failure(monkeypatch):
    """Overall status remains healthy/degraded. The dependency string carries the cause."""
    gateway._probe_cache.clear()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host != "converter.example":
            return httpx.Response(200)
        return httpx.Response(429, headers={"cf-mitigated": "challenge"})

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(
                gateway,
                "SERVICES",
                {
                    "auth": "https://auth.example",
                    "converter": "https://converter.example/",
                    "library": "https://library.example",
                },
            )
            return await gateway.detailed_health_check()

    result = asyncio.run(run())
    gateway._probe_cache.clear()
    assert result.status == "degraded"
    assert result.service_name == "api-gateway"
    assert result.dependencies["auth"] == "healthy"
    assert result.dependencies["library"] == "healthy"
    assert result.dependencies["converter"] == "unhealthy:GET /health HTTP 429 cloudflare-challenge"


def test_converter_health_proxy_falls_back_on_404_only(monkeypatch):
    """`/converter/health` tries `/health`, then `/` when that route is absent."""

    async def fake_forward(service_name, path, request, user=None, timeout=None):
        code = 404 if path == "/health" else 200
        return gateway.Response(content=b"{}", status_code=code, media_type="application/json")

    monkeypatch.setattr(gateway, "forward_request", fake_forward)
    response = asyncio.run(gateway.converter_health(None))
    assert response.status_code == 200

    calls = []

    async def only_health(service_name, path, request, user=None, timeout=None):
        calls.append(path)
        return gateway.Response(content=b"limited", status_code=429)

    monkeypatch.setattr(gateway, "forward_request", only_health)
    limited = asyncio.run(gateway.converter_health(None))
    assert calls == ["/health"]
    assert limited.status_code == 429


def test_probe_cache_stops_a_second_call(monkeypatch):
    """Repeated polls within the cache window must not hit the converter again."""
    gateway._probe_cache.clear()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200)

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(gateway, "PROBE_CACHE_SECONDS", 30)
            first = await gateway.probe_service("https://cache.example")
            second = await gateway.probe_service("https://cache.example")
            return first, second

    first, second = asyncio.run(run())
    gateway._probe_cache.clear()
    assert first == second == "healthy"
    assert seen == ["/health"]
