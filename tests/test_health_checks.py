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


def test_probe_falls_back_when_health_is_missing():
    """A 404 still means the route is absent, so ``/`` is the real check."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(404)
        assert request.url.path == "/"
        return httpx.Response(200, json={"status": "healthy"})

    status = _probe("https://converter.example/", handler)
    assert status == "healthy"
    assert seen == ["/health", "/"]


def test_probe_does_not_follow_a_rate_limit():
    """A 429 is the caller being limited, not a missing path.

    Requesting ``/`` immediately is a second hit from the same address and
    keeps Render's free-tier limit open. The routing header is kept so a
    wake-up 429 is visible without another request.
    """
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(429, headers={"x-render-routing": "hibernate-rate-limited"})

    status = _probe("https://converter.example/", handler)
    assert status == "unhealthy:GET converter.example/health HTTP 429 hibernate-rate-limited"
    assert seen == ["/health"]


def test_probe_marks_an_application_429():
    """A 429 that reached uvicorn is the app, not Render's edge."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"x-render-origin-server": "uvicorn"})

    status = _probe("https://converter.example", handler)
    assert status == "unhealthy:GET converter.example/health HTTP 429 from-app"


def test_probe_reports_both_status_codes_when_fallback_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(502)
        return httpx.Response(503)

    status = _probe("https://converter.example", handler)
    assert status == (
        "unhealthy:GET converter.example/health HTTP 502; GET converter.example/ HTTP 503"
    )


def test_probe_reports_exception_type_and_still_tries_root():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            raise httpx.TimeoutException("timed out")
        return httpx.Response(200)

    assert _probe("https://converter.example", handler) == "healthy"

    def both_fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    status = _probe("https://converter.example", both_fail)
    assert status == (
        "unavailable:GET converter.example/health ConnectError; "
        "GET converter.example/ ConnectError"
    )


def test_probe_stops_after_healthy_health_path():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200)

    assert _probe("https://converter.example", handler) == "healthy"
    assert seen == ["/health"]


def test_missing_service_url_is_unavailable_without_a_request():
    assert asyncio.run(gateway.probe_service("  ")) == "unavailable:MissingServiceUrl"


def _gateway_health(monkeypatch, handler):
    gateway.clear_health_probe_cache()

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

    return asyncio.run(run())


def test_gateway_health_stays_degraded_and_names_the_failure(monkeypatch):
    """Overall status remains healthy/degraded. A 429 does not cause a second GET."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.url.path))
        if request.url.host != "converter.example":
            return httpx.Response(200)
        return httpx.Response(429)

    result = _gateway_health(monkeypatch, handler)
    assert result.status == "degraded"
    assert result.service_name == "api-gateway"
    assert result.dependencies["auth"] == "healthy"
    assert result.dependencies["library"] == "healthy"
    assert result.dependencies["converter"] == "unhealthy:GET converter.example/health HTTP 429"
    assert ("converter.example", "/") not in seen


def test_detailed_health_reuses_a_recent_probe(monkeypatch):
    """Two quick /health calls must not hit the converter twice."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200)

    async def run():
        gateway.clear_health_probe_cache()
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(
                gateway,
                "SERVICES",
                {
                    "auth": "https://auth.example",
                    "converter": "https://converter.example",
                    "library": "https://library.example",
                },
            )
            first = await gateway.detailed_health_check()
            second = await gateway.detailed_health_check()
            return first, second

    first, second = asyncio.run(run())
    assert first.status == "healthy"
    assert second.status == "healthy"
    # Three services once. The second check is served from the cache.
    assert calls["n"] == 3


def test_outbound_headers_drop_cloudflare_replay_headers():
    """Forwarding CF-Ray to the next onrender.com host triggers a challenge."""
    headers = gateway.outbound_headers({
        "Host": "pdf-converter-api-gateway.onrender.com",
        "CF-Ray": "abc",
        "CF-Connecting-IP": "1.2.3.4",
        "X-Forwarded-For": "1.2.3.4",
        "X-User-ID": "spoofed",
        "Authorization": "Bearer t",
        "User-Agent": "diag-health/1.0",
        "Accept": "*/*",
    })
    lowered = {key.lower() for key in headers}
    assert "host" not in lowered
    assert "cf-ray" not in lowered
    assert "cf-connecting-ip" not in lowered
    assert "x-forwarded-for" not in lowered
    assert "x-user-id" not in lowered
    assert headers["Authorization"] == "Bearer t"
    assert headers["User-Agent"] == "diag-health/1.0"
    assert headers["Accept"] == "*/*"


def test_outbound_headers_set_gateway_user_agent_when_missing():
    headers = gateway.outbound_headers({"Accept": "*/*"})
    assert headers["User-Agent"] == "pdf-converter-gateway"


def test_probe_cache_ttl_backs_off_on_any_429():
    """Both the hibernate 429 and a header-less 429 wait out the penalty."""
    hibernate = "unhealthy:GET /health HTTP 429 hibernate-rate-limited"
    bare = "unhealthy:GET /health HTTP 429"
    assert gateway.probe_cache_ttl(hibernate) == gateway.RATE_LIMIT_PROBE_BACKOFF_SECONDS
    assert gateway.probe_cache_ttl(bare) == gateway.RATE_LIMIT_PROBE_BACKOFF_SECONDS
    assert gateway.probe_cache_ttl("healthy") == gateway.HEALTH_PROBE_CACHE_SECONDS
    assert gateway.probe_cache_ttl("unhealthy:GET /health HTTP 502; GET / HTTP 503") == (
        gateway.HEALTH_PROBE_CACHE_SECONDS
    )


def test_rate_limit_is_not_retried_on_the_short_cache_window(monkeypatch):
    """A 429 must not be probed again just because the 20s cache has expired.

    That retry is what kept auth, library, and the converter on
    hibernate-rate-limited after they were already returning 200 elsewhere.
    """
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"x-render-routing": "hibernate-rate-limited"})

    monkeypatch.setattr(gateway, "HEALTH_PROBE_CACHE_SECONDS", 0)

    async def run():
        gateway.clear_health_probe_cache()
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(
                gateway,
                "SERVICES",
                {
                    "auth": "https://auth.example",
                    "converter": "https://converter.example",
                    "library": "https://library.example",
                },
            )
            first = await gateway.detailed_health_check()
            second = await gateway.detailed_health_check()
            return first, second

    first, second = asyncio.run(run())
    assert first.status == "degraded"
    assert second.status == "degraded"
    for name in ("auth", "converter", "library"):
        assert first.dependencies[name] == (
            f"unhealthy:GET {name}.example/health HTTP 429 hibernate-rate-limited"
        )
        assert second.dependencies[name] == first.dependencies[name]
    # One request per service. The second /health is served from the backoff.
    assert calls["n"] == 3


def test_rate_limit_is_probed_again_after_the_backoff(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 3:
            return httpx.Response(429)
        return httpx.Response(200)

    monkeypatch.setattr(gateway, "RATE_LIMIT_PROBE_BACKOFF_SECONDS", 0)

    async def run():
        gateway.clear_health_probe_cache()
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(
                gateway,
                "SERVICES",
                {
                    "auth": "https://auth.example",
                    "converter": "https://converter.example",
                    "library": "https://library.example",
                },
            )
            first = await gateway.detailed_health_check()
            second = await gateway.detailed_health_check()
            return first, second

    first, second = asyncio.run(run())
    assert "HTTP 429" in first.dependencies["converter"]
    assert second.status == "healthy"
    assert calls["n"] == 6


def test_detailed_health_probes_again_after_the_cache_window(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200)

    monkeypatch.setattr(gateway, "HEALTH_PROBE_CACHE_SECONDS", 0)

    async def run():
        gateway.clear_health_probe_cache()
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(gateway, "http_client", client)
            monkeypatch.setattr(
                gateway,
                "SERVICES",
                {
                    "auth": "https://auth.example",
                    "converter": "https://converter.example",
                    "library": "https://library.example",
                },
            )
            await gateway.detailed_health_check()
            await gateway.detailed_health_check()

    asyncio.run(run())
    assert calls["n"] == 6
