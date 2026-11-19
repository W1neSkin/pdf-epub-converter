"""Call the PDFCalque Python module from the converter.

The module is the library itself: `import pdfcalque`. There is no separate program.
If the module is not installed, the existing Python pipeline still converts the file.
"""

import json

_last_failure = ""


def last_failure() -> str:
    """Short reason the last PDFCalque call produced no report."""
    return _last_failure


def _fail(reason: str) -> None:
    global _last_failure
    text = " ".join(str(reason).split())
    _last_failure = text[:240]


def read_report(pdf_path, epub_path=None):
    """
    Ask the library to read a PDF.

    When epub_path is set, the library also writes the EPUB.
    None means the module is missing or the PDF could not be read.
    """
    try:
        import pdfcalque
    except ImportError as err:
        _fail(f"pdfcalque module is not installed: {err}")
        return None
    try:
        if epub_path:
            raw = pdfcalque.export_epub(pdf_path, epub_path)
        else:
            raw = pdfcalque.report(pdf_path)
        return json.loads(raw)
    except Exception as err:
        _fail(str(err))
        return None


def prefer_pdfcalque_pages(report):
    """
    Use PDFCalque for a book with real text, and for a scan that is already a picture.

    A page made of vector drawings and almost no letters stays with Poppler:
    PDFCalque does not paint shadings and blends.
    """
    if not report:
        return False
    text = int(report.get("text_chars") or 0)
    pages = max(1, int(report.get("pages") or 0))
    scans = int(report.get("full_page_images") or 0)
    paths = int(report.get("paths") or 0)
    if scans * 2 >= pages and text < 80:
        return True
    if text >= 80:
        return True
    if paths > 40 and text < 80:
        return False
    return text > 0
