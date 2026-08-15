import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from table_extractor import write_tables_to_single_csv  # noqa: E402


def test_write_tables_to_single_csv_includes_strategy_and_cells():
    tables = [
        {
            "page": 1,
            "table_index": 1,
            "strategy": "lines_strict",
            "rows": [
                ["Date", "Amount"],
                ["2026-01-01", "1500"],
            ],
        },
        {
            "page": 2,
            "table_index": 1,
            "strategy": "text_balanced",
            "rows": [
                ["Category", "Value", "Notes"],
                ["Fees", "120", "Monthly"],
            ],
        },
    ]

    with tempfile.TemporaryDirectory(prefix="csv_writer_test_") as tmp_dir:
        output_path = Path(tmp_dir) / "tables.csv"
        row_count = write_tables_to_single_csv(tables, str(output_path))
        assert row_count == 4
        assert output_path.exists()

        with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))

        assert rows[0][:4] == ["page", "table_index", "row_index", "strategy"]
        assert "column_3" in rows[0]
        assert rows[1][0:4] == ["1", "1", "1", "lines_strict"]
        assert rows[4][0:4] == ["2", "1", "2", "text_balanced"]
        assert "Monthly" in rows[4]
