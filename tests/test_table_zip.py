import csv
import io
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from table_extractor import write_tables_to_zip  # noqa: E402


def test_each_extracted_table_gets_its_own_csv(tmp_path):
    """The separate download must preserve table boundaries and Unicode text."""
    tables = [
        {
            "page": 2,
            "table_index": 1,
            "rows": [["Имя", "Сумма"], ["Иван", "100"]],
        },
        {
            "page": 5,
            "table_index": 2,
            "rows": [["Date", "Status"], ["2026-08-19", "Paid"]],
        },
    ]
    archive_path = tmp_path / "separate_tables.zip"

    assert write_tables_to_zip(tables, str(archive_path)) == 2

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == [
            "page_002_table_01.csv",
            "page_005_table_02.csv",
        ]
        first_csv = archive.read("page_002_table_01.csv").decode("utf-8-sig")
        assert list(csv.reader(io.StringIO(first_csv))) == [
            ["Имя", "Сумма"],
            ["Иван", "100"],
        ]
