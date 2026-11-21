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
# Render polls a web service about every 5 seconds. Without a cache, each
# poll of this gateway's /health is another call from one IP to the converter,
# which Cloudflare then answers with a 429 challenge.
PROBE_CACHE_SECONDS = float(os.getenv("HEALTH_PROBE_CACHE_SECONDS", "20"))
_probe_cache: Dict[str, Tuple[float, str]] = {}


def normalize_service_base_url(service_url: str) -> str:
    """Drop whitespace and a trailing slash before appending a path.

    ``CONVERTER_SERVICE_URL`` is sometimes saved with a trailing slash.
    ``{url}/health`` would then request ``//health``, which is a different
    path and can 404 even when the service is up.
    """
    return (service_url or "").strip().rstrip("/")


def _http_failure_label(response: httpx.Response) -> str:
    """Status code, and a mark when Cloudflare issued the 429 challenge page."""
    label = f"HTTP {response.status_code}"
    # cf-mitigated: challenge is Cloudflare's bot/DDoS page, not our app.
    if response.headers.get("cf-mitigated"):
        label += " cloudflare-challenge"
    return label


async def probe_service(service_url: str, client: Optional[httpx.AsyncClient] = None) -> str:
    """Return ``healthy`` or a diagnosable ``unhealthy`` / ``unavailable`` string.

    ``GET /health`` is the shared check. A missing route (404) or a connection
    error falls back to ``GET /``. A 429 does not: that response is Cloudflare
    or Render telling this caller to stop, and a second path is the same caller.

    Results for the shared client are cached so a 5-second platform poll does
    not stampede the converter. Callers that pass a client always probe fresh.
    """
    base = normalize_service_base_url(service_url)
    if not base:
        return "unavailable:MissingServiceUrl"

    now = time.monotonic()
    if client is None:
        cached = _probe_cache.get(base)
        if cached and now - cached[0] < PROBE_CACHE_SECONDS:
            return cached[1]

    result = await _probe_service_once(base, client or http_client)
    if client is None:
        _probe_cache[base] = (now, result)
    return result


async def _probe_service_once(base: str, http: httpx.AsyncClient) -> str:
    """Probe one base URL. 429 stops the loop; other failures try `/`."""
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
        attempts.append(f"GET {path} {_http_failure_label(response)}")
        # Same source IP, same edge limit. Another GET would keep the 429 going.
        if response.status_code == 429:
            break

    # An HTTP status means the host answered. No response at all is unavailable.
    kind = "unhealthy" if saw_http else "unavailable"
    return f"{kind}:{'; '.join(attempts)}"


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
    """
    service_status = {}

    for service_name, service_url in SERVICES.items():
        result = await probe_service(service_url)
        if result != "healthy":
            logger.warning(
                "Health probe for %s (%s) returned %s",
                service_name,
                service_url,
                result,
            )
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
    """Proxy `/health`, then `/` if this converter build does not have that route.

    A 429 is returned as-is. Falling through to `/` would be a second request
    from the same caller that Cloudflare is already limiting.
    """
    response = await forward_request("converter", "/health", request)
    if response.status_code == 404:
        return await forward_request("converter", "/", request)
    return response

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