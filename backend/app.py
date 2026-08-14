from fastapi import FastAPI, File, UploadFile, HTTPException, status, Request, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
import shutil
from typing import Dict, Any, Optional
import logging
import jwt
from PyPDF2 import PdfReader
from conversion_jobs import read_status, run_conversion_job, write_status
from plan_limits import limits_for

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"
# Free-plan defaults. Paid tiers can pass a different plan later.
_FREE = limits_for("free")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(_FREE["max_file_mb"] * 1024 * 1024)))
MAX_PAGES = int(os.getenv("MAX_PAGES", str(_FREE["max_pages"])))

# Utility functions
def get_user_from_jwt(request: Request) -> Optional[Dict[str, Any]]:
    """Verify Bearer JWT. Do not trust client-supplied X-User-ID alone."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload["user_id"], "email": payload["email"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Require a valid JWT for conversion and downloads."""
    user = get_user_from_jwt(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required"
        )
    return user

def require_conversion_id(conversion_id: str) -> str:
    """Reject path-traversal style IDs. Jobs are always UUIDs."""
    try:
        return str(uuid.UUID(conversion_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion id")

# Pydantic models for request/response validation
class ConversionResponse(BaseModel):
    success: bool
    conversion_id: str
    download_url: Optional[str] = None
    pages: int
    total_words: int
    book_id: Optional[str] = None
    status: str = "processing"

class StatusResponse(BaseModel):
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    pages: Optional[int] = None
    current_page: Optional[int] = None
    total_words: Optional[int] = None
    book_id: Optional[str] = None

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
    allow_origins=[
        "https://w1neskin.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: Request = None,
    user: Dict[str, Any] = Depends(get_current_user)
) -> ConversionResponse:
    """Accept a PDF and start conversion in the background."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    # Do not require content_type == application/pdf. Browsers and the
    # gateway often send application/octet-stream for a real PDF.

    conversion_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{conversion_id}.pdf")
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE:
        os.remove(pdf_path)
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    try:
        page_count = len(PdfReader(pdf_path).pages)
    except Exception:
        os.remove(pdf_path)
        raise HTTPException(status_code=400, detail="Could not read PDF page count")

    if page_count > MAX_PAGES:
        os.remove(pdf_path)
        raise HTTPException(
            status_code=400,
            detail=f"PDF has too many pages ({page_count}). Maximum is {MAX_PAGES}"
        )

    output_dir = os.path.join(OUTPUT_FOLDER, conversion_id)
    os.makedirs(output_dir, exist_ok=True)
    write_status(
        output_dir,
        status="processing",
        progress=10,
        message="Upload received. Conversion queued...",
        pages=page_count,
    )

    auth_header = request.headers.get("Authorization", "") if request else ""
    background_tasks.add_task(
        run_conversion_job,
        conversion_id,
        pdf_path,
        output_dir,
        file.filename,
        user,
        auth_header,
    )
    logger.info("Queued conversion %s for %s", conversion_id, file.filename)

    return ConversionResponse(
        success=True,
        conversion_id=conversion_id,
        download_url=None,
        pages=page_count,
        total_words=0,
        status="processing",
    )

@app.get("/api/download/{conversion_id}")
async def download_epub(
    conversion_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Download the generated EPUB file"""
    conversion_id = require_conversion_id(conversion_id)
    epub_path = os.path.join(OUTPUT_FOLDER, conversion_id, f"{conversion_id}.epub")
    if not os.path.exists(epub_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=epub_path,
        filename=f"converted_{conversion_id}.epub",
        media_type='application/epub+zip'
    )

@app.get("/api/status/{conversion_id}", response_model=StatusResponse)
async def get_conversion_status(
    conversion_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> StatusResponse:
    """Return live conversion progress from status.json."""
    conversion_id = require_conversion_id(conversion_id)
    output_dir = os.path.join(OUTPUT_FOLDER, conversion_id)
    job = read_status(output_dir)
    if not job:
        raise HTTPException(status_code=404, detail="Conversion not found")
    return StatusResponse(
        status=job.get("status", "processing"),
        progress=job.get("progress"),
        message=job.get("message"),
        file_size=job.get("file_size"),
        download_url=job.get("download_url"),
        pages=job.get("pages"),
        current_page=job.get("current_page"),
        total_words=job.get("total_words"),
        book_id=job.get("book_id"),
    )

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
