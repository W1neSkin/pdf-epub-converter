"""
Shared configuration for PDF to EPUB Converter microservices
Used across all services: Gateway, Auth, Converter, Library
"""

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Shared settings across all microservices"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Cloudinary Configuration
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Service URLs (for inter-service communication)
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    CONVERTER_SERVICE_URL: str = os.getenv("CONVERTER_SERVICE_URL", "http://localhost:8000")
    LIBRARY_SERVICE_URL: str = os.getenv("LIBRARY_SERVICE_URL", "http://localhost:8002")
    GATEWAY_SERVICE_URL: str = os.getenv("GATEWAY_SERVICE_URL", "http://localhost:8080")
    
    # Frontend URL
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://w1neskin.github.io/pdf-epub-converter")
    
    # CORS Settings
    ALLOWED_ORIGINS: list = [
        "https://w1neskin.github.io",
        "http://localhost:3000",  # Local development
        "http://127.0.0.1:3000"   # Local development
    ]
    
    # File Storage
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: list = ["application/pdf"]
    UPLOAD_DIR: str = "/tmp/uploads"
    
    # Rate Limiting (free tier friendly)
    RATE_LIMIT_REQUESTS: int = 100  # requests per minute
    RATE_LIMIT_WINDOW: int = 60     # seconds
    
    # Session Configuration
    SESSION_EXPIRATION_HOURS: int = 24
    CLEANUP_SESSIONS_INTERVAL: int = 3600  # seconds (1 hour)
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Service-specific configurations
class AuthServiceSettings(Settings):
    """Auth service specific settings"""
    SERVICE_NAME: str = "auth-service"
    PORT: int = int(os.getenv("PORT", "8001"))

class ConverterServiceSettings(Settings):
    """Converter service specific settings"""
    SERVICE_NAME: str = "converter-service"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # PDF Processing
    PDF_TIMEOUT: int = 300  # 5 minutes
    MAX_PAGES: int = 100    # Free tier limit
    
class LibraryServiceSettings(Settings):
    """Library service specific settings"""
    SERVICE_NAME: str = "library-service"
    PORT: int = int(os.getenv("PORT", "8002"))
    
    # Library limits (free tier)
    MAX_BOOKS_PER_USER: int = 50
    MAX_STORAGE_PER_USER: int = 1024 * 1024 * 1024  # 1GB

class GatewayServiceSettings(Settings):
    """API Gateway specific settings"""
    SERVICE_NAME: str = "api-gateway"
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Gateway configuration
    TIMEOUT: int = 60  # seconds
    MAX_RETRIES: int = 3 