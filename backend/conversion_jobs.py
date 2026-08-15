"""
Simple file-based conversion jobs.
No extra queue service: one Render instance writes status.json and the
frontend polls /api/status. This avoids gateway timeouts on large PDFs.
"""
import json
import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

from alternative_parser import AlternativePDFParser
from epub_generator import EPUBGenerator
from html_generator import HTMLPageGenerator
from storage import storage

logger = logging.getLogger(__name__)

# Local default is localhost. On Render the converter has no LIBRARY_SERVICE_URL,
# so fall back to the live library service so converted books get saved.
LIBRARY_SERVICE_URL = os.getenv(
    "LIBRARY_SERVICE_URL",
    "https://pdf-converter-library-service.onrender.com",
)


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
        def report(progress: int, message: str, current_page: int = 0, pages: int = 0) -> None:
            # Live status for the progress bar. Do not invent large jumps.
            write_status(
                output_dir,
                status="processing",
                progress=progress,
                message=message,
                current_page=current_page or None,
                pages=pages or None,
            )

        report(8, "Reading the PDF...")
        processor = AlternativePDFParser()
        results = processor.parse_pdf(pdf_path, output_dir, on_progress=report)

        pages_data = results.get("pages", [])
        page_count = len(pages_data)
        report(55, "Building EPUB pages...", pages=page_count)
        html_generator = HTMLPageGenerator()
        html_files = html_generator.generate_html_pages(pages_data=pages_data, output_dir=output_dir)
        if not html_files:
            raise Exception("No pages generated from PDF")

        report(80, "Packaging EPUB...", pages=page_count)
        epub_path = os.path.join(output_dir, f"{conversion_id}.epub")
        language = _detect_language(results.get("total_text", ""))
        EPUBGenerator().generate_epub(
            html_dir=output_dir,
            image_dir=output_dir,
            output_filename=epub_path,
            title=f"Converted PDF - {filename}",
            language=language,
        )

        report(90, "Saving EPUB...", pages=page_count)
        upload_result = storage.upload_epub(epub_path, conversion_id)
        if upload_result:
            download_url = upload_result["secure_url"]
        else:
            # Absolute gateway URL. A relative /api/download path opens on GitHub Pages.
            gateway = os.getenv(
                "PUBLIC_API_URL",
                "https://pdf-converter-api-gateway.onrender.com",
            )
            download_url = f"{gateway}/api/download/{conversion_id}"
            logger.warning("Cloudinary upload failed, using local fallback")

        total_words = results.get("total_words", 0)
        book_id = _save_to_library(
            filename=filename,
            file_size=os.path.getsize(epub_path),
            pages=page_count,
            words=total_words,
            download_url=download_url,
            conversion_id=conversion_id,
            user=user,
            auth_header=auth_header,
            language=language,
        )

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        write_status(
            output_dir,
            status="completed",
            progress=100,
            message="Conversion completed",
            download_url=download_url,
            pages=page_count,
            total_words=total_words,
            book_id=book_id,
            file_size=os.path.getsize(epub_path),
        )
        logger.info("Conversion %s completed: %s pages", conversion_id, page_count)
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
    language: str,
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
            "language": language,
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


def _detect_language(text: str) -> str:
    """
    Very small language heuristic for metadata.

    The test file contains Cyrillic. Marking it as "ru" helps readers select
    better fonts/hyphenation than hardcoding "en".
    """
    if not text:
        return "en"
    cyrillic = len(re.findall(r"[А-Яа-яЁёІіЎў]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cyrillic > latin:
        return "ru"
    return "en"
