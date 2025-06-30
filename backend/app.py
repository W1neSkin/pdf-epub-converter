from fastapi import FastAPI, File, UploadFile, HTTPException, status
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
from alternative_parser import PDFProcessor
from html_generator import HTMLGenerator
from epub_generator import EPUBGenerator
from storage import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class ConversionResponse(BaseModel):
    success: bool
    conversion_id: str
    download_url: str
    pages: int
    total_words: int

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
async def convert_pdf_to_epub(file: UploadFile = File(...)) -> ConversionResponse:
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
            processor = PDFProcessor()
            results = processor.process_pdf(pdf_path, output_dir)
            
            # Generate HTML pages
            html_gen = HTMLGenerator()
            html_pages = html_gen.generate_html_pages(results, output_dir)
            
            # Generate EPUB
            epub_gen = EPUBGenerator()
            epub_path = epub_gen.create_epub(
                results, 
                html_pages, 
                output_dir,
                f"{conversion_id}.epub"
            )
            
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
        
        logger.info(f"Successfully converted PDF {file.filename} to EPUB. Pages: {len(results.get('pages', []))}, Words: {results.get('total_words', 0)}")
        
        return ConversionResponse(
            success=True,
            conversion_id=conversion_id,
            download_url=download_url,
            pages=len(results.get('pages', [])),
            total_words=results.get('total_words', 0)
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