import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from table_extractor import _rows_from_ocr_data  # noqa: E402


def test_rows_from_ocr_data_groups_lines_and_splits_columns():
    ocr_data = {
        "text": ["Invoice", "No.", "12345", "Total", "99.50", ""],
        "conf": ["96", "95", "94", "93", "92", "-1"],
        "left": [10, 62, 160, 10, 160, 0],
        "top": [10, 10, 10, 34, 34, 0],
        "width": [45, 20, 50, 30, 40, 0],
        "height": [12, 12, 12, 12, 12, 0],
    }

    rows = _rows_from_ocr_data(ocr_data)
    assert rows == [
        ["Invoice No.", "12345"],
        ["Total", "99.50"],
    ]
