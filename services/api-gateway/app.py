"""
API Gateway for PDF to EPUB Converter
Routes requests to appropriate microservices
Handles authentication, routing, and CORS
"""

import os
import sys
import logging
import asyncio
import time
from typing import Optional, Dict, Any, Tuple
import httpx
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import jwt

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.config import GatewayServiceSettings
from shared.models import ErrorResponse, HealthCheck

# Initialize settings
settings = GatewayServiceSettings()

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF to EPUB Converter - API Gateway",
    description="API Gateway for microservices routing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Service URLs
SERVICES = {
    "auth": settings.AUTH_SERVICE_URL,
    "converter": settings.CONVERTER_SERVICE_URL,
    "library": settings.LIBRARY_SERVICE_URL
}

# HTTP client for inter-service communication
http_client = httpx.AsyncClient(timeout=settings.TIMEOUT)
RENDER_WAKE_RETRY_ATTEMPTS = int(os.getenv("RENDER_WAKE_RETRY_ATTEMPTS", "30"))
RENDER_WAKE_RETRY_DELAY_SECONDS = float(os.getenv("RENDER_WAKE_RETRY_DELAY_SECONDS", "6"))


def is_hibernate_rate_limited(response: httpx.Response) -> bool:
    """True when Render rejects requests while a sleeping service wakes up."""
    if response.status_code != 429:
        return False
    routing = response.headers.get("x-render-routing", "")
    return "hibernate-rate-limited" in routing.lower()


async def send_with_render_retry(
    service_name: str,
    method: str,
    target_url: str,
    request_timeout: float,
    **kwargs: Any,
) -> httpx.Response:
    """Retry requests when Render returns hibernate-rate-limited 429."""
    response: Optional[httpx.Response] = None
    for attempt in range(1, RENDER_WAKE_RETRY_ATTEMPTS + 1):
        response = await http_client.request(
            method,
            target_url,
            timeout=request_timeout,
            **kwargs,
        )
        if not is_hibernate_rate_limited(response):
            return response

        if attempt == RENDER_WAKE_RETRY_ATTEMPTS:
            logger.error(
                "Service %s stayed hibernate-rate-limited after %s attempts",
                service_name,
                RENDER_WAKE_RETRY_ATTEMPTS,
            )
            return response

        logger.warning(
            "Service %s is waking up (attempt %s/%s), retrying in %.1fs",
            service_name,
            attempt,
            RENDER_WAKE_RETRY_ATTEMPTS,
            RENDER_WAKE_RETRY_DELAY_SECONDS,
        )
        await asyncio.sleep(RENDER_WAKE_RETRY_DELAY_SECONDS)

    return response  # Unreachable, kept for type safety.

# Utility Functions
def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token (optional)"""
    if not credentials:
        return None
    
    try:
        payload = verify_jwt_token(credentials.credentials)
        return payload
    except HTTPException:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token (required)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    payload = verify_jwt_token(credentials.credentials)
    return payload

async def forward_request(
    service_name: str,
    path: str,
    request: Request,
    user: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None
) -> Response:
    """Forward request to microservice"""
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found"
        )
    
    # A trailing slash on the env URL would turn "/health" into "//health".
    service_url = normalize_service_base_url(service_url)
    target_url = f"{service_url}{path}"
    
    # Prepare headers
    headers = dict(request.headers)
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    # Never trust client-supplied user headers; only set them from a verified JWT.
    headers.pop("x-user-id", None)
    headers.pop("X-User-ID", None)
    headers.pop("x-user-email", None)
    headers.pop("X-User-Email", None)
    
    # Add user context if available
    if user:
        headers["X-User-ID"] = user["user_id"]
        headers["X-User-Email"] = user["email"]

    request_timeout = timeout or settings.TIMEOUT
    
    try:
        # Forward the request
        if request.method == "GET":
            response = await send_with_render_retry(
                service_name=service_name,
                method="GET",
                target_url=target_url,
                request_timeout=request_timeout,
                headers=headers,
                params=request.query_params,
            )
        elif request.method == "POST":
            if request.headers.get("content-type", "").startswith("multipart/form-data"):
                # Handle file uploads
                form_data = await request.form()
                files = {}
                data = {}
                
                for key, value in form_data.items():
                    if hasattr(value, 'read'):  # File upload
                        # Keep PDF uploads as application/pdf. Some browsers send octet-stream.
                        content_type = value.content_type
                        if value.filename and str(value.filename).lower().endswith('.pdf'):
                            content_type = 'application/pdf'
                        files[key] = (value.filename, await value.read(), content_type)
                    else:
                        data[key] = value
                
                # Drop the original body headers. httpx builds a new multipart body.
                response = await send_with_render_retry(
                    service_name=service_name,
                    method="POST",
                    target_url=target_url,
                    request_timeout=request_timeout,
                    headers={
                        k: v for k, v in headers.items()
                        if k.lower() not in ("content-type", "content-length")
                    },
                    files=files,
                    data=data,
                    # Keep ?output=excel when the file is sent as multipart.
                    params=request.query_params,
                )
            else:
                # Handle JSON/other content
                body = await request.body()
                response = await send_with_render_retry(
                    service_name=service_name,
                    method="POST",
                    target_url=target_url,
                    request_timeout=request_timeout,
                    headers=headers,
                    content=body,
                )
        elif request.method == "PUT":
            body = await request.body()
            response = await send_with_render_retry(
                service_name=service_name,
                method="PUT",
                target_url=target_url,
                request_timeout=request_timeout,
                headers=headers,
                content=body,
            )
        elif request.method == "DELETE":
            response = await send_with_render_retry(
                service_name=service_name,
                method="DELETE",
                target_url=target_url,
                request_timeout=request_timeout,
                headers=headers,
                params=request.query_params,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=f"Method {request.method} not allowed"
            )
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout forwarding request to {service_name}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Service {service_name} timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Error forwarding request to {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Service {service_name} unavailable"
        )

# One slow dependency must not hold the whole gateway health response open.
HEALTH_PROBE_TIMEOUT = 5.0
# A normal result can be reused briefly. Render may call /health every few
# seconds; this stops that from becoming a downstream call every time.
HEALTH_PROBE_CACHE_SECONDS = 20.0
# A 429 is different. Render's hibernate-rate-limited penalty, and Cloudflare
# in front of the public URL, keep answering 429 to a caller that tries again
# too soon. 20s is inside that window, so the gateway stayed degraded for
# minutes while a direct call already returned 200. One wake-up, then be quiet
# long enough for the free instance to finish booting (~1 minute) before the
# single retry. Applies to auth, library, and the converter.
RATE_LIMIT_PROBE_BACKOFF_SECONDS = 90.0
# /health must answer inside Render's 5s health-check limit. Probes run
# together and this request does not wait longer than this.
HEALTH_PROBE_BUDGET_SECONDS = 4.0
# base URL -> (monotonic time, probe result)
_health_probe_cache: Dict[str, Tuple[float, str]] = {}
# base URL -> in-flight probe. Callers share it so they do not stampede.
_health_probe_inflight: Dict[str, "asyncio.Task[str]"] = {}
_health_probe_lock = asyncio.Lock()


def normalize_service_base_url(service_url: str) -> str:
    """Drop whitespace and a trailing slash before appending a path.

    ``CONVERTER_SERVICE_URL`` is sometimes saved with a trailing slash.
    ``{url}/health`` would then request ``//health``, which is a different
    path and can 404 even when the service is up.
    """
    return (service_url or "").strip().rstrip("/")


def describe_probe_http(path: str, response: httpx.Response) -> str:
    """One failed attempt, plus the header that says who produced a 429.

    ``x-render-routing: hibernate-rate-limited`` is Render's edge while a
    free instance is waking up. That response never reaches the app, so it
    has no ``x-render-origin-server``. A 429 from our own code (the public
    conversion cap) does reach uvicorn and sets that header. The cap is not
    applied to ``/`` or ``/health``.
    """
    text = f"GET {path} HTTP {response.status_code}"
    routing = (response.headers.get("x-render-routing") or "").strip()
    if routing:
        return f"{text} {routing}"
    if response.headers.get("x-render-origin-server"):
        return f"{text} from-app"
    return text


def clear_health_probe_cache() -> None:
    """Drop cached probes. Tests call this so one case cannot satisfy the next."""
    _health_probe_cache.clear()
    _health_probe_inflight.clear()


def probe_cache_ttl(result: str) -> float:
    """Seconds to wait before probing this result again.

    Any HTTP 429 uses the long backoff. That covers Render's
    ``hibernate-rate-limited`` response and a later 429 from Cloudflare that
    no longer carries the routing header. Other results use the short cache.
    """
    if "HTTP 429" in result:
        return RATE_LIMIT_PROBE_BACKOFF_SECONDS
    return HEALTH_PROBE_CACHE_SECONDS


def _cached_probe_result(base: str) -> Optional[str]:
    cached = _health_probe_cache.get(base)
    if not cached:
        return None
    probed_at, result = cached
    if time.monotonic() - probed_at >= probe_cache_ttl(result):
        return None
    return result


async def probe_service(service_url: str, client: Optional[httpx.AsyncClient] = None) -> str:
    """Return ``healthy`` or a diagnosable ``unhealthy`` / ``unavailable`` string.

    ``GET /health`` is the shared check (auth, library, and the converter).
    A 404 or a 5xx falls back to ``GET /``: an older converter only implements
    ``/``, and a cold start often answers 502/503 on the first try.

    A 429 does not fall back. Render's free tier returns 429 for the caller,
    not for one path (``hibernate-rate-limited`` while the instance wakes, or
    the lower inbound limit once that caller has sent too many requests).
    ``GET /`` from the same caller gets the same 429, and the extra request
    is what keeps the limit open. Direct calls from another address can still
    be 200. User-facing proxy calls already wait 6 seconds between hibernate
    retries. This probe must not fire a second request immediately.

    Failure strings keep the old word and append what failed, for example
    ``unhealthy:GET /health HTTP 429 hibernate-rate-limited`` or
    ``unhealthy:GET /health HTTP 502; GET / HTTP 503`` or
    ``unavailable:GET /health TimeoutException``.
    """
    base = normalize_service_base_url(service_url)
    if not base:
        return "unavailable:MissingServiceUrl"

    http = client or http_client
    attempts = []
    saw_http = False

    for path in ("/health", "/"):
        try:
            response = await http.get(f"{base}{path}", timeout=HEALTH_PROBE_TIMEOUT)
        except Exception as exc:
            # Still try `/`. A timeout on `/health` during wake-up often
            # clears by the time the root path is requested.
            attempts.append(f"GET {path} {type(exc).__name__}")
            continue

        if response.status_code == 200:
            return "healthy"

        saw_http = True
        attempts.append(describe_probe_http(path, response))
        if response.status_code == 429:
            break

    # An HTTP status means the host answered. No response at all is unavailable.
    kind = "unhealthy" if saw_http else "unavailable"
    return f"{kind}:{'; '.join(attempts)}"


async def _probe_and_store(base: str) -> str:
    """Run one probe and remember it. The caller must not cancel this task."""
    try:
        result = await probe_service(base)
    except Exception as exc:
        # A cancelled or failed probe must not be cached as a 429, or the
        # backoff would hide a service that is already up.
        result = f"unavailable:{type(exc).__name__}"
    if base:
        _health_probe_cache[base] = (time.monotonic(), result)
    return result


async def cached_probe_service(service_url: str) -> str:
    """Return a recent probe, or start one and share it with other callers.

    A 200 is reused for ``HEALTH_PROBE_CACHE_SECONDS``. A 429 is reused for
    ``RATE_LIMIT_PROBE_BACKOFF_SECONDS`` so auth, library, and the converter
    are each woken once and then left alone until the free-tier penalty ends.
    Overlapping ``/health`` calls await the same in-flight probe.
    """
    base = normalize_service_base_url(service_url)
    cached = _cached_probe_result(base)
    if cached is not None:
        return cached

    async with _health_probe_lock:
        cached = _cached_probe_result(base)
        if cached is not None:
            return cached
        task = _health_probe_inflight.get(base)
        if task is None or task.done():
            task = asyncio.create_task(_probe_and_store(base))
            if base:
                _health_probe_inflight[base] = task
    return await task


# Routes

@app.get("/", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {
        "service": "api-gateway",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", response_model=HealthCheck)
async def detailed_health_check():
    """Detailed health check with service dependencies.

    Overall ``status`` stays ``healthy`` or ``degraded``. Each dependency is
    ``healthy``, or ``unhealthy`` / ``unavailable`` plus the status code or
    exception type from the probe.

    The three probes run together. This response waits at most
    ``HEALTH_PROBE_BUDGET_SECONDS`` so a slow 429 cannot blow Render's 5s
    health-check limit and restart the gateway. The probe itself keeps
    running and fills the cache for the next call.
    """
    service_status = {}

    async def one(service_name: str, service_url: str):
        task = asyncio.create_task(cached_probe_service(service_url))
        try:
            # shield: hitting the budget must not cancel the probe. Cancelling
            # it would miss the cache write and the next call would try again
            # immediately, which is what keeps a 429 alive.
            result = await asyncio.wait_for(asyncio.shield(task), timeout=HEALTH_PROBE_BUDGET_SECONDS)
        except asyncio.TimeoutError:
            cached = _cached_probe_result(normalize_service_base_url(service_url))
            result = cached if cached is not None else "unavailable:ProbeTimeout"
        if result != "healthy":
            logger.warning(
                "Health probe for %s (%s) returned %s",
                service_name,
                service_url,
                result,
            )
        return service_name, result

    for service_name, result in await asyncio.gather(
        *(one(name, url) for name, url in SERVICES.items())
    ):
        service_status[service_name] = result

    all_healthy = all(status == "healthy" for status in service_status.values())

    return HealthCheck(
        service_name="api-gateway",
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database_connected=True,  # Gateway doesn't have direct DB connection
        dependencies=service_status
    )

# Authentication routes (no auth required)
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request):
    """Proxy requests to auth service"""
    return await forward_request("auth", f"/auth/{path}", request)

# Converter routes require a logged-in user, except the public conversion API.
@app.api_route("/api/public/{path:path}", methods=["GET", "POST"])
async def public_convert_proxy(path: str, request: Request):
    """Proxy anonymous conversion, status, and download calls."""
    return await forward_request(
        "converter",
        f"/api/public/{path}",
        request,
        timeout=settings.CONVERT_TIMEOUT,
    )


@app.api_route("/api/convert", methods=["POST"])
async def convert_proxy(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy PDF conversion requests to converter service"""
    # No convert rate limit: retries while Render wakes were counted as real jobs.
    return await forward_request(
        "converter",
        "/api/convert",
        request,
        user,
        timeout=settings.CONVERT_TIMEOUT
    )


@app.api_route("/api/extract-tables", methods=["POST"])
async def extract_tables_proxy(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy PDF table extraction requests to converter service"""
    return await forward_request(
        "converter",
        "/api/extract-tables",
        request,
        user,
        timeout=settings.CONVERT_TIMEOUT
    )

@app.api_route("/api/download/{file_id}", methods=["GET"])
async def download_proxy(file_id: str, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy download requests to converter service"""
    return await forward_request("converter", f"/api/download/{file_id}", request, user)

@app.api_route("/api/status/{conversion_id}", methods=["GET"])
async def status_proxy(conversion_id: str, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy status requests to converter service"""
    return await forward_request("converter", f"/api/status/{conversion_id}", request, user)

# Library routes (auth required)
@app.api_route("/library/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def library_proxy(path: str, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy requests to library service (auth required)"""
    return await forward_request("library", f"/library/{path}", request, user)

# Converter service health check. `/` on the converter stays the Render probe.
@app.get("/converter/health")
async def converter_health(request: Request):
    """Proxy the converter's `/health` check (same path as auth and library)."""
    return await forward_request("converter", "/health", request)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with a consistent JSON envelope."""
    error = ErrorResponse(
        success=False,
        error_code="GATEWAY_ERROR",
        message=exc.detail,
        details={"status_code": exc.status_code, "path": str(request.url)}
    )
    return JSONResponse(status_code=exc.status_code, content=error.model_dump(mode="json"))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup"""
    logger.info("API Gateway starting up...")
    logger.info(f"Auth Service: {SERVICES['auth']}")
    logger.info(f"Converter Service: {SERVICES['converter']}")
    logger.info(f"Library Service: {SERVICES['library']}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API Gateway shutting down...")
    await http_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 