"""
Simple file-based conversion jobs.
No extra queue service: one Render instance writes status.json and the
frontend polls /api/status. This avoids gateway timeouts on large PDFs.
"""
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from alternative_parser import AlternativePDFParser
from epub_generator import EPUBGenerator
from html_generator import HTMLPageGenerator
from storage import storage

logger = logging.getLogger(__name__)

LIBRARY_SERVICE_URL = os.getenv("LIBRARY_SERVICE_URL", "http://localhost:8002")


def status_path(output_dir: str) -> str:
    return os.path.join(output_dir, "status.json")


def write_status(output_dir: str, **fields: Any) -> None:
    """Merge fields into status.json so the poll endpoint can read progress."""
    os.makedirs(output_dir, exist_ok=True)
    path = status_path(output_dir)
    current: Dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                current = json.load(handle)
        except Exception:
            current = {}
    current.update(fields)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(current, handle)


def read_status(output_dir: str) -> Optional[Dict[str, Any]]:
    path = status_path(output_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def run_conversion_job(
    conversion_id: str,
    pdf_path: str,
    output_dir: str,
    filename: str,
    user: Dict[str, Any],
    auth_header: str,
) -> None:
    """Run the full PDF -> EPUB pipeline and update status.json as it goes."""
    try:
        write_status(
            output_dir,
            status="processing",
            progress=20,
            message="Extracting text and page images...",
        )
        processor = AlternativePDFParser()
        results = processor.parse_pdf(pdf_path, output_dir)

        write_status(
            output_dir,
            status="processing",
            progress=50,
            message="Building interactive HTML pages...",
        )
        html_generator = HTMLPageGenerator()
        html_files = html_generator.generate_html_pages(
            pdf_path=pdf_path,
            image_dir=output_dir,
            output_dir=output_dir,
        )
        if not html_files:
            raise Exception("No pages generated from PDF")

        write_status(
            output_dir,
            status="processing",
            progress=75,
            message="Packaging EPUB...",
        )
        epub_path = os.path.join(output_dir, f"{conversion_id}.epub")
        EPUBGenerator().generate_epub(
            html_dir=output_dir,
            image_dir=output_dir,
            output_filename=epub_path,
            title=f"Converted PDF - {filename}",
        )

        write_status(
            output_dir,
            status="processing",
            progress=90,
            message="Uploading EPUB...",
        )
        upload_result = storage.upload_epub(epub_path, conversion_id)
        if upload_result:
            download_url = upload_result["secure_url"]
        else:
            download_url = f"/api/download/{conversion_id}"
            logger.warning("Cloudinary upload failed, using local fallback")

        pages = len(results.get("pages", []))
        total_words = results.get("total_words", 0)
        book_id = _save_to_library(
            filename=filename,
            file_size=os.path.getsize(epub_path),
            pages=pages,
            words=total_words,
            download_url=download_url,
            conversion_id=conversion_id,
            user=user,
            auth_header=auth_header,
        )

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        write_status(
            output_dir,
            status="completed",
            progress=100,
            message="Conversion completed",
            download_url=download_url,
            pages=pages,
            total_words=total_words,
            book_id=book_id,
            file_size=os.path.getsize(epub_path),
        )
        logger.info("Conversion %s completed: %s pages", conversion_id, pages)
    except Exception as exc:
        logger.error("Conversion %s failed: %s", conversion_id, exc)
        write_status(
            output_dir,
            status="failed",
            progress=0,
            message=str(exc),
        )
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass


def _save_to_library(
    filename: str,
    file_size: int,
    pages: int,
    words: int,
    download_url: str,
    conversion_id: str,
    user: Dict[str, Any],
    auth_header: str,
) -> Optional[str]:
    """Best-effort library save. Conversion still succeeds if this fails."""
    title = filename.replace(".pdf", "")
    book_data = {
        "title": title,
        "original_filename": filename,
        "file_size": file_size,
        "pages": pages,
        "words": words,
        "cloudinary_url": download_url,
        "file_path": f"conversions/{conversion_id}.epub",
        "metadata": {
            "title": title,
            "description": "Converted from PDF",
            "language": "en",
        },
        "is_public": False,
    }
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{LIBRARY_SERVICE_URL}/library/books",
                json=book_data,
                headers={
                    "Authorization": auth_header,
                    "X-User-ID": user["user_id"],
                    "X-User-Email": user["email"],
                },
                timeout=10.0,
            )
        if response.status_code == 200:
            payload = response.json()
            if payload.get("success"):
                return str(payload["data"]["id"])
        logger.warning("Library save failed: %s", response.status_code)
    except Exception as exc:
        logger.error("Error saving book to library: %s", exc)
    return None
