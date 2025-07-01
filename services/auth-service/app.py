"""
Authentication Service for PDF to EPUB Converter
Handles user registration, login, JWT tokens, and user profile management
Uses Supabase for authentication backend
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from supabase import create_client, Client
import bcrypt
from pydantic import ValidationError

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.config import AuthServiceSettings
from shared.models import (
    UserRegister, UserLogin, AuthResponse, AuthToken, ErrorResponse,
    UserProfile, UserProfileCreate, UserProfileUpdate, HealthCheck
)

# Initialize settings
settings = AuthServiceSettings()

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF to EPUB Converter - Auth Service",
    description="Authentication and user management microservice",
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

# Initialize Supabase clients
# Auth operations use anon key, admin operations use service key
supabase_auth: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Security
security = HTTPBearer(auto_error=False)

# Utility Functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str) -> Dict[str, Any]:
    """Create JWT token for user"""
    expiration = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRATION_HOURS * 3600,
        "user_id": UUID(user_id)  # Convert string to UUID for Pydantic validation
    }

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    payload = verify_jwt_token(credentials.credentials)
    return payload

# Routes

@app.get("/", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {
        "service": "auth-service",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", response_model=HealthCheck)
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Test Supabase connection using admin client
        result = supabase_admin.table('user_profiles').select("id").limit(1).execute()
        db_connected = True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_connected = False
    
    return HealthCheck(
        service_name="auth-service",
        status="healthy" if db_connected else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        dependencies={
            "supabase": "connected" if db_connected else "failed"
        }
    )

@app.post("/debug/register")
async def debug_register_user(user_data: UserRegister):
    """Debug registration endpoint with detailed error reporting"""
    try:
        logger.info(f"DEBUG: Starting registration for {user_data.email}")
        
        # Test basic Supabase auth connection
        logger.info("DEBUG: Testing Supabase auth connection...")
        
        # Create user in Supabase Auth using anon key
        logger.info("DEBUG: Calling supabase_auth.auth.sign_up...")
        auth_response = supabase_auth.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        })
        
        logger.info(f"DEBUG: Auth response received: {auth_response}")
        
        if not auth_response.user:
            logger.error("DEBUG: No user in auth response")
            return {"error": "No user in auth response", "response": str(auth_response)}
        
        user_id = auth_response.user.id
        logger.info(f"DEBUG: User created with ID: {user_id}")
        
        # Create JWT token
        logger.info("DEBUG: Creating JWT token...")
        token_data = create_jwt_token(user_id, user_data.email)
        logger.info(f"DEBUG: Token created: {token_data}")
        
        # Try to create AuthToken object
        logger.info("DEBUG: Creating AuthToken object...")
        auth_token = AuthToken(**token_data)
        logger.info(f"DEBUG: AuthToken created: {auth_token}")
        
        return {
            "success": True,
            "message": "Debug registration successful", 
            "user_id": user_id,
            "token_data": token_data
        }
        
    except Exception as e:
        logger.error(f"DEBUG: Registration failed with error: {e}")
        logger.error(f"DEBUG: Error type: {type(e)}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        
        return {
            "error": str(e),
            "error_type": str(type(e)),
            "traceback": traceback.format_exc()
        }

@app.post("/auth/register", response_model=AuthResponse)
async def register_user(user_data: UserRegister):
    """Register a new user"""
    try:
        # Create user in Supabase Auth using anon key
        auth_response = supabase_auth.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )
        
        user_id = auth_response.user.id
        
        # Create user profile (bypass RLS with service role)
        profile_data = {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "subscription_tier": "free",
            "storage_used": 0,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Use admin client to bypass RLS for profile creation
        try:
            result = supabase_admin.table('user_profiles').insert(profile_data).execute()
            logger.info(f"Profile created successfully for user: {user_data.email}")
        except Exception as profile_error:
            logger.error(f"Profile creation failed: {profile_error}")
            # Continue anyway - profile can be created later
            pass
        
        # Create JWT token
        token_data = create_jwt_token(user_id, user_data.email)
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            data=AuthToken(**token_data)
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        error_message = str(e).lower()
        
        # Handle specific Supabase errors
        if "already registered" in error_message or "email already exists" in error_message or "user already exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/auth/login", response_model=AuthResponse)
async def login_user(user_data: UserLogin):
    """Login user and return JWT token"""
    try:
        # Authenticate with Supabase using anon key
        auth_response = supabase_auth.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user_id = auth_response.user.id
        
        # Create JWT token
        token_data = create_jwt_token(user_id, user_data.email)
        
        logger.info(f"User logged in successfully: {user_data.email}")
        
        return AuthResponse(
            success=True,
            message="Login successful",
            data=AuthToken(**token_data)
        )
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

@app.post("/auth/logout")
async def logout_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (invalidate token on client side)"""
    try:
        # In a stateless JWT system, logout is handled client-side
        # We could add token blacklisting here if needed
        
        logger.info(f"User logged out: {current_user['email']}")
        
        return {
            "success": True,
            "message": "Logout successful"
        }
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@app.get("/auth/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verify JWT token and return user info"""
    try:
        # Get user profile from database using admin client
        result = supabase_admin.table('user_profiles').select("*").eq('id', current_user['user_id']).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile = result.data[0]
        
        return {
            "success": True,
            "user": {
                "id": profile['id'],
                "email": profile['email'],
                "full_name": profile['full_name'],
                "avatar_url": profile['avatar_url'],
                "subscription_tier": profile['subscription_tier'],
                "storage_used": profile['storage_used']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )

@app.get("/auth/profile", response_model=UserProfile)
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's profile"""
    try:
        result = supabase_admin.table('user_profiles').select("*").eq('id', current_user['user_id']).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile = result.data[0]
        return UserProfile(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )

@app.put("/auth/profile", response_model=UserProfile)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update current user's profile"""
    try:
        # Prepare update data
        update_data = {}
        if profile_update.full_name is not None:
            update_data['full_name'] = profile_update.full_name
        if profile_update.avatar_url is not None:
            update_data['avatar_url'] = profile_update.avatar_url
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Update user profile using admin client
        result = supabase_admin.table('user_profiles').update(update_data).eq('id', current_user['user_id']).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        updated_profile = result.data[0]
        logger.info(f"Profile updated for user: {current_user['email']}")
        
        return UserProfile(**updated_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return ErrorResponse(
        success=False,
        error_code="VALIDATION_ERROR",
        message="Invalid input data",
        details={"errors": exc.errors()}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return ErrorResponse(
        success=False,
        error_code="HTTP_ERROR",
        message=exc.detail,
        details={"status_code": exc.status_code}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 