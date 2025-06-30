"""
Shared models for PDF to EPUB Converter microservices
Pydantic models for API validation and SQLAlchemy models for database
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

# Enums
class ConversionStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SubscriptionTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"

class PermissionLevel(str, Enum):
    READ = "read"
    DOWNLOAD = "download"

# Base Models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# User Models
class UserProfile(BaseModel):
    """User profile model"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    storage_used: int = 0  # in bytes
    created_at: datetime
    updated_at: datetime

class UserProfileCreate(BaseModel):
    """User profile creation model"""
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserProfileUpdate(BaseModel):
    """User profile update model"""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

# Authentication Models
class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    """User registration model"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class AuthToken(BaseModel):
    """Authentication token model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: UUID

class AuthResponse(BaseResponse):
    """Authentication response"""
    success: bool = True
    data: AuthToken

# Book Models
class BookMetadata(BaseModel):
    """Book metadata model"""
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = "en"
    publisher: Optional[str] = None
    publish_date: Optional[datetime] = None
    isbn: Optional[str] = None
    genres: List[str] = []

class UserBook(BaseModel):
    """User book model"""
    id: UUID
    user_id: UUID
    title: str
    original_filename: str
    file_size: int
    pages: Optional[int] = None
    words: Optional[int] = None
    cloudinary_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    file_path: Optional[str] = None
    metadata: BookMetadata = Field(default_factory=BookMetadata)
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

class UserBookCreate(BaseModel):
    """User book creation model"""
    title: str
    original_filename: str
    file_size: int
    pages: Optional[int] = None
    words: Optional[int] = None
    cloudinary_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[BookMetadata] = None
    is_public: bool = False

class UserBookUpdate(BaseModel):
    """User book update model"""
    title: Optional[str] = None
    metadata: Optional[BookMetadata] = None
    is_public: Optional[bool] = None

class UserBookResponse(BaseResponse):
    """User book response"""
    success: bool = True
    data: UserBook

class UserBooksResponse(BaseResponse):
    """User books list response"""
    success: bool = True
    data: List[UserBook]
    total: int
    page: int = 1
    limit: int = 50

# Conversion Models
class ConversionJob(BaseModel):
    """Conversion job model"""
    id: UUID
    user_id: UUID
    book_id: Optional[UUID] = None
    original_filename: str
    conversion_status: ConversionStatus = ConversionStatus.PROCESSING
    pages: Optional[int] = None
    words: Optional[int] = None
    processing_time: Optional[int] = None  # in seconds
    error_message: Optional[str] = None
    conversion_metadata: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None

class ConversionJobCreate(BaseModel):
    """Conversion job creation model"""
    original_filename: str
    conversion_metadata: Dict[str, Any] = {}

class ConversionJobUpdate(BaseModel):
    """Conversion job update model"""
    conversion_status: Optional[ConversionStatus] = None
    pages: Optional[int] = None
    words: Optional[int] = None
    processing_time: Optional[int] = None
    error_message: Optional[str] = None
    conversion_metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

class ConversionResponse(BaseResponse):
    """Conversion response"""
    success: bool = True
    conversion_id: UUID
    download_url: str
    pages: Optional[int] = None
    total_words: Optional[int] = None

# Sharing Models
class SharedBook(BaseModel):
    """Shared book model"""
    id: UUID
    book_id: UUID
    owner_id: UUID
    shared_with_id: UUID
    permission_level: PermissionLevel = PermissionLevel.READ
    shared_at: datetime

class SharedBookCreate(BaseModel):
    """Shared book creation model"""
    book_id: UUID
    shared_with_email: EmailStr
    permission_level: PermissionLevel = PermissionLevel.READ

class SharedBookResponse(BaseResponse):
    """Shared book response"""
    success: bool = True
    data: SharedBook

# Session Models
class UserSession(BaseModel):
    """User session model"""
    id: UUID
    user_id: UUID
    session_token: str
    expires_at: datetime
    last_activity: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

# File Upload Models
class FileUploadResponse(BaseResponse):
    """File upload response"""
    success: bool = True
    file_id: str
    filename: str
    file_size: int
    upload_url: Optional[str] = None

# Library Statistics
class LibraryStats(BaseModel):
    """User library statistics"""
    total_books: int
    total_size: int  # in bytes
    total_pages: int
    total_words: int
    recent_conversions: int  # last 30 days
    storage_used_percent: float

class LibraryStatsResponse(BaseResponse):
    """Library statistics response"""
    success: bool = True
    data: LibraryStats

# API Health Models
class HealthCheck(BaseModel):
    """Health check model"""
    service_name: str
    status: str
    version: str
    timestamp: datetime
    database_connected: bool
    dependencies: Dict[str, str] = {}

# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

class PaginatedResponse(BaseResponse):
    """Paginated response"""
    success: bool = True
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool 