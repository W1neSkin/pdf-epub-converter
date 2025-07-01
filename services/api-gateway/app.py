"""
API Gateway for PDF to EPUB Converter
Routes requests to appropriate microservices
Handles authentication, rate limiting, and CORS
"""

import os
import sys
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
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
    user: Optional[Dict[str, Any]] = None
) -> Response:
    """Forward request to microservice"""
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found"
        )
    
    # Build target URL
    target_url = f"{service_url}{path}"
    
    # Prepare headers
    headers = dict(request.headers)
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    
    # Add user context if available
    if user:
        headers["X-User-ID"] = user["user_id"]
        headers["X-User-Email"] = user["email"]
    
    try:
        # Forward the request
        if request.method == "GET":
            response = await http_client.get(
                target_url,
                headers=headers,
                params=request.query_params
            )
        elif request.method == "POST":
            if request.headers.get("content-type", "").startswith("multipart/form-data"):
                # Handle file uploads
                form_data = await request.form()
                files = {}
                data = {}
                
                for key, value in form_data.items():
                    if hasattr(value, 'read'):  # File upload
                        files[key] = (value.filename, await value.read(), value.content_type)
                    else:
                        data[key] = value
                
                response = await http_client.post(
                    target_url,
                    headers={k: v for k, v in headers.items() if k.lower() != "content-type"},
                    files=files,
                    data=data
                )
            else:
                # Handle JSON/other content
                body = await request.body()
                response = await http_client.post(
                    target_url,
                    headers=headers,
                    content=body
                )
        elif request.method == "PUT":
            body = await request.body()
            response = await http_client.put(
                target_url,
                headers=headers,
                content=body
            )
        elif request.method == "DELETE":
            response = await http_client.delete(
                target_url,
                headers=headers,
                params=request.query_params
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
    """Detailed health check with service dependencies"""
    service_status = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            response = await http_client.get(f"{service_url}/", timeout=5.0)
            service_status[service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            service_status[service_name] = "unavailable"
    
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

# Converter routes (auth optional for now, will be required later)
@app.api_route("/api/convert", methods=["POST"])
async def convert_proxy(request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Proxy PDF conversion requests to converter service"""
    return await forward_request("converter", "/api/convert", request, user)

@app.api_route("/api/download/{file_id}", methods=["GET"])
async def download_proxy(file_id: str, request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Proxy download requests to converter service"""
    return await forward_request("converter", f"/api/download/{file_id}", request, user)

@app.api_route("/api/status/{conversion_id}", methods=["GET"])
async def status_proxy(conversion_id: str, request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Proxy status requests to converter service"""
    return await forward_request("converter", f"/api/status/{conversion_id}", request, user)

# Library routes (auth required)
@app.api_route("/library/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def library_proxy(path: str, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Proxy requests to library service (auth required)"""
    return await forward_request("library", f"/library/{path}", request, user)

# Converter service health check
@app.get("/converter/health")
async def converter_health(request: Request):
    """Check converter service health"""
    return await forward_request("converter", "/", request)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return ErrorResponse(
        success=False,
        error_code="GATEWAY_ERROR",
        message=exc.detail,
        details={"status_code": exc.status_code, "path": str(request.url)}
    )

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