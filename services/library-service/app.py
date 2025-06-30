"""
Library Service for PDF to EPUB Converter
Handles user book collections, metadata, sharing, and file management
Uses Supabase for data storage and Cloudinary for file storage
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import math

from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
from pydantic import ValidationError

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.config import LibraryServiceSettings
from shared.models import (
    UserBook, UserBookCreate, UserBookUpdate, UserBooksResponse, UserBookResponse,
    LibraryStats, LibraryStatsResponse, SharedBook, SharedBookCreate, SharedBookResponse,
    HealthCheck, ErrorResponse, PaginationParams, PaginatedResponse,
    ConversionJob, ConversionJobCreate
)

# Initialize settings
settings = LibraryServiceSettings()

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF to EPUB Converter - Library Service",
    description="User book library and metadata management microservice",
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

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Initialize Cloudinary
if settings.CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)

# Security
security = HTTPBearer(auto_error=False)

# Utility Functions
def get_user_from_headers(request: Request) -> Optional[Dict[str, Any]]:
    """Extract user info from gateway headers"""
    user_id = request.headers.get("X-User-ID")
    user_email = request.headers.get("X-User-Email")
    
    if user_id and user_email:
        return {
            "user_id": user_id,
            "email": user_email
        }
    return None

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user (required)"""
    user = get_user_from_headers(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required"
        )
    return user

async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user (optional)"""
    return get_user_from_headers(request)

def calculate_pagination(page: int, limit: int, total: int) -> Dict[str, Any]:
    """Calculate pagination metadata"""
    total_pages = math.ceil(total / limit) if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }

# Routes

@app.get("/")
def health_check():
    return {"service": "library-service", "status": "healthy"}

@app.get("/health", response_model=HealthCheck)
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Test Supabase connection
        result = supabase.table('user_books').select("id").limit(1).execute()
        db_connected = True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_connected = False
    
    # Test Cloudinary connection
    cloudinary_connected = bool(settings.CLOUDINARY_URL)
    
    return HealthCheck(
        service_name="library-service",
        status="healthy" if db_connected else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        dependencies={
            "supabase": "connected" if db_connected else "failed",
            "cloudinary": "connected" if cloudinary_connected else "not_configured"
        }
    )

@app.get("/library/books", response_model=UserBooksResponse)
async def get_user_books(
    pagination: PaginationParams = Depends(),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user's book library with pagination"""
    try:
        user_id = user["user_id"]
        
        # Calculate offset
        offset = (pagination.page - 1) * pagination.limit
        
        # Get total count
        count_result = supabase.table('user_books').select("id", count="exact").eq('user_id', user_id).execute()
        total = count_result.count or 0
        
        # Get books with pagination
        query = (supabase.table('user_books')
                .select("*")
                .eq('user_id', user_id)
                .order(pagination.sort_by, desc=(pagination.sort_order == "desc"))
                .range(offset, offset + pagination.limit - 1))
        
        result = query.execute()
        books = [UserBook(**book) for book in result.data] if result.data else []
        
        # Calculate pagination metadata
        pagination_meta = calculate_pagination(pagination.page, pagination.limit, total)
        
        return UserBooksResponse(
            success=True,
            data=books,
            **pagination_meta
        )
        
    except Exception as e:
        logger.error(f"Failed to get user books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books"
        )

@app.get("/library/books/{book_id}", response_model=UserBookResponse)
async def get_book(
    book_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific book by ID"""
    try:
        user_id = user["user_id"]
        
        # Check if user owns the book or has access to it
        result = supabase.table('user_books').select("*").eq('id', str(book_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        book_data = result.data[0]
        
        # Check access permissions
        if book_data['user_id'] != user_id:
            # Check if book is shared with user
            shared_result = supabase.table('shared_books').select("*").eq('book_id', str(book_id)).eq('shared_with_id', user_id).execute()
            
            if not shared_result.data and not book_data.get('is_public', False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this book"
                )
        
        book = UserBook(**book_data)
        return UserBookResponse(success=True, data=book)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book"
        )

@app.post("/library/books", response_model=UserBookResponse)
async def create_book(
    book_data: UserBookCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new book in user's library"""
    try:
        user_id = user["user_id"]
        
        # Check storage limits for free tier
        stats = await get_library_statistics(user)
        if stats.data.total_books >= settings.MAX_BOOKS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Maximum number of books reached ({settings.MAX_BOOKS_PER_USER})"
            )
        
        if stats.data.total_size + book_data.file_size > settings.MAX_STORAGE_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Storage limit exceeded"
            )
        
        # Create book record
        book_record = {
            "user_id": user_id,
            "title": book_data.title,
            "original_filename": book_data.original_filename,
            "file_size": book_data.file_size,
            "pages": book_data.pages,
            "words": book_data.words,
            "cloudinary_url": book_data.cloudinary_url,
            "cover_image_url": book_data.cover_image_url,
            "file_path": book_data.file_path,
            "metadata": book_data.metadata.dict() if book_data.metadata else {},
            "is_public": book_data.is_public
        }
        
        result = supabase.table('user_books').insert(book_record).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create book record"
            )
        
        # Update user storage usage
        new_storage = stats.data.total_size + book_data.file_size
        supabase.table('user_profiles').update({"storage_used": new_storage}).eq('id', user_id).execute()
        
        book = UserBook(**result.data[0])
        logger.info(f"Book created: {book.title} for user {user['email']}")
        
        return UserBookResponse(
            success=True,
            data=book,
            message="Book added to library successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book"
        )

@app.put("/library/books/{book_id}", response_model=UserBookResponse)
async def update_book(
    book_id: UUID,
    book_update: UserBookUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update book metadata"""
    try:
        user_id = user["user_id"]
        
        # Check if user owns the book
        result = supabase.table('user_books').select("*").eq('id', str(book_id)).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Prepare update data
        update_data = {}
        if book_update.title is not None:
            update_data['title'] = book_update.title
        if book_update.metadata is not None:
            update_data['metadata'] = book_update.metadata.dict()
        if book_update.is_public is not None:
            update_data['is_public'] = book_update.is_public
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Update book
        result = supabase.table('user_books').update(update_data).eq('id', str(book_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update book"
            )
        
        book = UserBook(**result.data[0])
        logger.info(f"Book updated: {book.title} by user {user['email']}")
        
        return UserBookResponse(
            success=True,
            data=book,
            message="Book updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book"
        )

@app.delete("/library/books/{book_id}")
async def delete_book(
    book_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a book from user's library"""
    try:
        user_id = user["user_id"]
        
        # Get book info first
        result = supabase.table('user_books').select("*").eq('id', str(book_id)).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        book_data = result.data[0]
        file_size = book_data.get('file_size', 0)
        
        # Delete book record
        supabase.table('user_books').delete().eq('id', str(book_id)).execute()
        
        # Update user storage usage
        current_storage = supabase.table('user_profiles').select("storage_used").eq('id', user_id).execute()
        if current_storage.data:
            new_storage = max(0, current_storage.data[0]['storage_used'] - file_size)
            supabase.table('user_profiles').update({"storage_used": new_storage}).eq('id', user_id).execute()
        
        logger.info(f"Book deleted: {book_data['title']} by user {user['email']}")
        
        return {
            "success": True,
            "message": "Book deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book"
        )

@app.get("/library/stats", response_model=LibraryStatsResponse)
async def get_library_statistics(user: Dict[str, Any] = Depends(get_current_user)):
    """Get user's library statistics"""
    try:
        user_id = user["user_id"]
        
        # Get book statistics
        books_result = supabase.table('user_books').select("file_size, pages, words, created_at").eq('user_id', user_id).execute()
        
        books = books_result.data or []
        total_books = len(books)
        total_size = sum(book.get('file_size', 0) for book in books)
        total_pages = sum(book.get('pages', 0) for book in books if book.get('pages'))
        total_words = sum(book.get('words', 0) for book in books if book.get('words'))
        
        # Calculate recent conversions (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_conversions = len([
            book for book in books 
            if book.get('created_at') and datetime.fromisoformat(book['created_at'].replace('Z', '+00:00')) > thirty_days_ago
        ])
        
        # Calculate storage usage percentage
        storage_used_percent = (total_size / settings.MAX_STORAGE_PER_USER) * 100 if settings.MAX_STORAGE_PER_USER > 0 else 0
        
        stats = LibraryStats(
            total_books=total_books,
            total_size=total_size,
            total_pages=total_pages,
            total_words=total_words,
            recent_conversions=recent_conversions,
            storage_used_percent=min(storage_used_percent, 100.0)
        )
        
        return LibraryStatsResponse(success=True, data=stats)
        
    except Exception as e:
        logger.error(f"Failed to get library stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get library statistics"
        )

@app.post("/library/share", response_model=SharedBookResponse)
async def share_book(
    share_data: SharedBookCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Share a book with another user"""
    try:
        user_id = user["user_id"]
        
        # Verify user owns the book
        book_result = supabase.table('user_books').select("*").eq('id', str(share_data.book_id)).eq('user_id', user_id).execute()
        
        if not book_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Find the user to share with
        user_result = supabase.table('user_profiles').select("id").eq('email', share_data.shared_with_email).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        shared_with_id = user_result.data[0]['id']
        
        # Check if already shared
        existing_share = supabase.table('shared_books').select("*").eq('book_id', str(share_data.book_id)).eq('shared_with_id', shared_with_id).execute()
        
        if existing_share.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book is already shared with this user"
            )
        
        # Create share record
        share_record = {
            "book_id": str(share_data.book_id),
            "owner_id": user_id,
            "shared_with_id": shared_with_id,
            "permission_level": share_data.permission_level.value
        }
        
        result = supabase.table('shared_books').insert(share_record).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to share book"
            )
        
        shared_book = SharedBook(**result.data[0])
        logger.info(f"Book shared: {book_result.data[0]['title']} with {share_data.shared_with_email}")
        
        return SharedBookResponse(
            success=True,
            data=shared_book,
            message="Book shared successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to share book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share book"
        )

@app.get("/library/shared")
async def get_shared_books(
    pagination: PaginationParams = Depends(),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get books shared with the current user"""
    try:
        user_id = user["user_id"]
        
        # Get shared books with book details
        offset = (pagination.page - 1) * pagination.limit
        
        # This would require a more complex query in a real implementation
        # For now, return a simple response
        return {
            "success": True,
            "data": [],
            "total": 0,
            "page": pagination.page,
            "limit": pagination.limit,
            "message": "Shared books feature coming soon"
        }
        
    except Exception as e:
        logger.error(f"Failed to get shared books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get shared books"
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
        error_code="LIBRARY_ERROR",
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