import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pdfcalque_bridge import prefer_pdfcalque_pages  # noqa: E402
import table_extractor  # noqa: E402


def test_text_book_uses_pdfcalque_pages():
    assert prefer_pdfcalque_pages({"text_chars": 5000, "pages": 10, "full_page_images": 0, "paths": 20})


def test_scan_uses_the_picture_already_in_the_pdf():
    assert prefer_pdfcalque_pages({"text_chars": 0, "pages": 4, "full_page_images": 4, "paths": 0})


def test_vector_art_stays_with_poppler():
    assert not prefer_pdfcalque_pages({"text_chars": 12, "pages": 1, "full_page_images": 0, "paths": 200})


def test_page_keeps_the_richer_table():
    ours = [{"page": 1, "rows": [["A", "1"], ["B", "2"], ["C", "3"]], "bbox": [0, 0, 10, 10]}]
    theirs = [{"rows": [["A"]], "score": 1.0}]
    assert table_extractor._pdfcalque_wins(ours, theirs[0]["score"])

    weak = [{"page": 1, "rows": [["A"]], "bbox": [0, 0, 10, 10]}]
    assert not table_extractor._pdfcalque_wins(weak, 30.0)


def test_long_prose_columns_score_as_zero():
    rows = [
        ["lacus vel est. Curabitur consectetuer.", "luctus et ultrices posuere cubilia Curae"],
        ["Suspendisse vel felis. Ut lorem lorem, interdum", "sit amet pede ac sem eleifend"],
    ]
    assert table_extractor._rows_score(rows) == 0
