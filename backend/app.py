from fastapi import FastAPI, File, UploadFile, HTTPException, status, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import tempfile
import json
import uuid
import shutil
from typing import Dict, Any, Optional
import asyncio
import logging
import httpx
from alternative_parser import AlternativePDFParser
from html_generator import HTMLPageGenerator
from epub_generator import EPUBGenerator
from storage import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LIBRARY_SERVICE_URL = os.getenv("LIBRARY_SERVICE_URL", "http://localhost:8002")

# Utility functions
def get_user_from_headers(request: Request) -> Optional[Dict[str, Any]]:
    """Extract user info from gateway headers"""
    user_id = request.headers.get("X-User-ID")
    user_email = request.headers.get("X-User-Email")
    
    if user_id and user_email:
        return {"user_id": user_id, "email": user_email}
    return None

async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user (optional for backward compatibility)"""
    return get_user_from_headers(request)

# Pydantic models for request/response validation
class ConversionResponse(BaseModel):
    success: bool
    conversion_id: str
    download_url: str
    pages: int
    total_words: int
    book_id: Optional[str] = None  # New field for library integration

class StatusResponse(BaseModel):
    status: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

app = FastAPI(
    title="PDF to EPUB Converter API",
    description="Convert PDF files to interactive EPUB with selectable text overlays",
    version="1.0.0"
)

# Enable CORS for GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directories
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="PDF to EPUB Converter API",
        version="1.0.0"
    )

@app.post("/api/convert", response_model=ConversionResponse)
async def convert_pdf_to_epub(
    file: UploadFile = File(...),
    request: Request = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> ConversionResponse:
    """Convert PDF file to EPUB with interactive text overlays"""
    
    # Validate file
    if not file.filename:
        logger.warning("Upload attempt with no filename")
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.lower().endswith('.pdf'):
        logger.warning(f"Upload attempt with invalid extension: {file.filename}")
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    if file.content_type and not file.content_type == 'application/pdf':
        logger.warning(f"Upload attempt with invalid MIME type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    logger.info(f"Starting PDF conversion for file: {file.filename}")
    
    try:
        # Generate unique ID for this conversion
        conversion_id = str(uuid.uuid4())
        
        # Save uploaded file
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{conversion_id}.pdf")
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create output directory for this conversion
        output_dir = os.path.join(OUTPUT_FOLDER, conversion_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Process PDF (run in thread pool for CPU-intensive work)
        loop = asyncio.get_event_loop()
        
        def process_pdf_sync():
            processor = AlternativePDFParser()
            results = processor.parse_pdf(pdf_path, output_dir)
            
            # Create simple HTML files for each page
            html_files = []
            for page_data in results.get('pages', []):
                if 'image_path' in page_data:
                    page_num = page_data['page_number']
                    image_filename = os.path.basename(page_data['image_path'])
                    
                    # Create simple HTML content
                    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PDF Page {page_num}</title>
</head>
<body>
    <h1>PDF Page {page_num}</h1>
    <img src="images/{image_filename}" alt="Page {page_num}" style="max-width: 100%; height: auto;"/>
    <p>Text content: {page_data.get('text', 'No text extracted')[:200]}...</p>
</body>
</html>'''
                    
                    # Save HTML file
                    html_filename = f"page_{page_num:03d}.html"
                    html_path = os.path.join(output_dir, html_filename)
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    html_files.append(html_path)
                    print(f"📄 Created HTML file: {html_path}")
            
            print(f"📁 Output directory contents: {os.listdir(output_dir)}")
            print(f"🔢 Total HTML files created: {len(html_files)}")
            
            # Generate EPUB from HTML files
            if html_files:
                epub_gen = EPUBGenerator()
                epub_filename = f"{conversion_id}.epub"
                epub_path = epub_gen.generate_epub(
                    html_dir=output_dir,
                    image_dir=output_dir,
                    output_filename=os.path.join(output_dir, epub_filename),
                    title=f"Converted PDF - {file.filename}"
                )
                print(f"✅ EPUB generated successfully: {epub_path}")
            else:
                raise Exception("No pages generated from PDF")
            
            return results
        
        results = await loop.run_in_executor(None, process_pdf_sync)
        
        # Upload EPUB to Cloudinary
        epub_path = os.path.join(output_dir, f"{conversion_id}.epub")
        upload_result = storage.upload_epub(epub_path, conversion_id)
        
        if upload_result:
            download_url = upload_result["secure_url"]
            logger.info(f"EPUB uploaded to Cloudinary: {upload_result['public_id']}")
        else:
            # Fallback to local download
            download_url = f"/api/download/{conversion_id}"
            logger.warning("Cloudinary upload failed, using local fallback")
        
        # Clean up local files
        os.remove(pdf_path)
        # Keep local EPUB for fallback, but could clean up later
        
        book_id = None
        
        # Save to user's library if authenticated
        if user:
            try:
                # Get file size
                file_size = os.path.getsize(epub_path)
                
                # Prepare book data for library service
                book_data = {
                    "title": file.filename.replace('.pdf', ''),
                    "original_filename": file.filename,
                    "file_size": file_size,
                    "pages": len(results.get('pages', [])),
                    "words": results.get('total_words', 0),
                    "cloudinary_url": download_url,
                    "file_path": f"conversions/{conversion_id}.epub",
                    "metadata": {
                        "conversion_id": conversion_id,
                        "original_format": "pdf",
                        "converted_format": "epub"
                    },
                    "is_public": False
                }
                
                # Send to library service
                async with httpx.AsyncClient() as client:
                    headers = {
                        "X-User-ID": user["user_id"],
                        "X-User-Email": user["email"]
                    }
                    response = await client.post(
                        f"{LIBRARY_SERVICE_URL}/library/books",
                        json=book_data,
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        library_response = response.json()
                        if library_response.get("success"):
                            book_id = str(library_response["data"]["id"])
                            logger.info(f"Book saved to library with ID: {book_id}")
                        else:
                            logger.warning(f"Library service returned error: {library_response}")
                    else:
                        logger.warning(f"Failed to save book to library: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"Error saving book to library: {e}")
                # Don't fail the conversion if library save fails
        
        logger.info(f"Successfully converted PDF {file.filename} to EPUB. Pages: {len(results.get('pages', []))}, Words: {results.get('total_words', 0)}")
        
        return ConversionResponse(
            success=True,
            conversion_id=conversion_id,
            download_url=download_url,
            pages=len(results.get('pages', [])),
            total_words=results.get('total_words', 0),
            book_id=book_id
        )
        
    except Exception as e:
        logger.error(f"Error converting PDF {file.filename}: {str(e)}")
        # Clean up on error
        try:
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@app.get("/api/download/{conversion_id}")
async def download_epub(conversion_id: str):
    """Download the generated EPUB file"""
    try:
        epub_path = os.path.join(OUTPUT_FOLDER, conversion_id, f"{conversion_id}.epub")
        
        if not os.path.exists(epub_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=epub_path,
            filename=f"converted_{conversion_id}.epub",
            media_type='application/epub+zip'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{conversion_id}", response_model=StatusResponse)
async def get_conversion_status(conversion_id: str) -> StatusResponse:
    """Get the status of a PDF conversion"""
    try:
        output_dir = os.path.join(OUTPUT_FOLDER, conversion_id)
        epub_path = os.path.join(output_dir, f"{conversion_id}.epub")
        
        if os.path.exists(epub_path):
            file_size = os.path.getsize(epub_path)
            return StatusResponse(
                status="completed",
                file_size=file_size,
                download_url=f"/api/download/{conversion_id}"
            )
        else:
            return StatusResponse(status="processing")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port) 