"""PDFCalque command used by the converter when the binary is available.

The binary writes an EPUB and a JSON report. This module decides which result
to keep. A missing binary is not an error: the Python pipeline stays in place.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def binary():
    """Path to pdfcalque, or None when this machine does not have it."""
    env = os.environ.get("PDFCALQUE_BIN", "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("pdfcalque") or shutil.which("pdfcalque.exe")
    if found:
        return found
    here = Path(__file__).resolve().parent
    # bin/ is produced by build.sh. The sibling checkout is the local dev build.
    checkout = here.parents[1] / "PDFCalque" / "target" / "release"
    candidates = []
    for name in ("pdfcalque.exe", "pdfcalque"):
        candidates.append(here / "bin" / name)
        candidates.append(checkout / name)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def read_report(pdf_path, epub_path=None):
    """
    Run PDFCalque.

    epub_path writes the book and the report. Without it, only the report is written.
    None means the tool is missing or the PDF could not be read.
    """
    program = binary()
    if not program:
        return None
    with tempfile.TemporaryDirectory(prefix="pdfcalque_") as tmp:
        json_path = Path(tmp) / "report.json"
        if epub_path:
            command = [program, "export", pdf_path, epub_path, str(json_path)]
        else:
            command = [program, "tables", pdf_path, str(json_path)]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0 or not json_path.is_file():
            return None
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
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
