import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CloudinaryStorage:
    """Storage service using Cloudinary for file management"""
    
    def __init__(self):
        """Initialize Cloudinary with environment variables"""
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            api_key=os.getenv('CLOUDINARY_API_KEY'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET'),
            secure=True
        )
        
        # Verify configuration
        if not all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ]):
            logger.warning("Cloudinary environment variables not set. File uploads will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Cloudinary storage initialized successfully")
    
    def upload_epub(self, file_path: str, conversion_id: str) -> Optional[Dict[str, Any]]:
        """Upload EPUB file to Cloudinary"""
        if not self.enabled:
            logger.warning("Cloudinary not configured, skipping upload")
            return None
            
        try:
            # Upload with specific options for EPUB files
            result = cloudinary.uploader.upload(
                file_path,
                public_id=f"epubs/{conversion_id}",
                resource_type="raw",  # For non-image files
                format="epub",
                tags=["epub", "converted"],
                context={"conversion_id": conversion_id}
            )
            
            logger.info(f"Successfully uploaded EPUB to Cloudinary: {result['public_id']}")
            
            return {
                "public_id": result["public_id"],
                "secure_url": result["secure_url"],
                "url": result["url"],
                "bytes": result["bytes"],
                "format": result["format"],
                "resource_type": result["resource_type"]
            }
            
        except Exception as e:
            logger.error(f"Failed to upload EPUB to Cloudinary: {str(e)}")
            return None
    
    def upload_pdf_page(self, file_path: str, conversion_id: str, page_number: int) -> Optional[Dict[str, Any]]:
        """Upload PDF page image to Cloudinary"""
        if not self.enabled:
            return None
            
        try:
            result = cloudinary.uploader.upload(
                file_path,
                public_id=f"pdf-pages/{conversion_id}/page_{page_number:03d}",
                resource_type="image",
                format="png",
                tags=["pdf-page", conversion_id],
                context={"conversion_id": conversion_id, "page": str(page_number)}
            )
            
            return {
                "public_id": result["public_id"],
                "secure_url": result["secure_url"],
                "url": result["url"]
            }
            
        except Exception as e:
            logger.error(f"Failed to upload PDF page to Cloudinary: {str(e)}")
            return None
    
    def get_download_url(self, public_id: str) -> Optional[str]:
        """Get secure download URL for a file"""
        if not self.enabled:
            return None
            
        try:
            url, options = cloudinary_url(
                public_id,
                resource_type="raw",
                secure=True,
                attachment=True  # Force download
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            return None
    
    def delete_file(self, public_id: str) -> bool:
        """Delete file from Cloudinary"""
        if not self.enabled:
            return False
            
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="raw"
            )
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Failed to delete file from Cloudinary: {str(e)}")
            return False
    
    def cleanup_conversion(self, conversion_id: str) -> None:
        """Clean up all files related to a conversion"""
        if not self.enabled:
            return
            
        try:
            # Delete EPUB
            self.delete_file(f"epubs/{conversion_id}")
            
            # Delete PDF pages (search by tag)
            cloudinary.api.delete_resources_by_tag(conversion_id)
            
            logger.info(f"Cleaned up Cloudinary files for conversion {conversion_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup Cloudinary files: {str(e)}")

# Global storage instance
storage = CloudinaryStorage() 