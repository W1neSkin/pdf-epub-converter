import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from document_csv import build_page_records, write_document_csv  # noqa: E402
import table_extractor  # noqa: E402


class FakePage:
    """Return positioned words like pdfplumber does."""

    @staticmethod
    def extract_words(**_kwargs):
        return [
            {"text": "Кредитный", "x0": 10, "x1": 70, "top": 10, "bottom": 20},
            {"text": "отчёт", "x0": 75, "x1": 110, "top": 10, "bottom": 20},
            {"text": "Имя", "x0": 10, "x1": 35, "top": 50, "bottom": 60},
            {"text": "Сумма", "x0": 110, "x1": 150, "top": 50, "bottom": 60},
            {"text": "Конец", "x0": 10, "x1": 45, "top": 120, "bottom": 130},
        ]


def test_page_records_keep_order_without_repeating_table_words():
    tables = [
        {
            "table_index": 1,
            "strategy": "lines_strict",
            "bbox": [0, 40, 200, 100],
            "rows": [["Имя", "Сумма"], ["Иван", "100"]],
        }
    ]

    records = build_page_records(FakePage(), 3, tables)

    assert [record["content_type"] for record in records] == [
        "text",
        "table",
        "table",
        "text",
    ]
    assert [record["content_order"] for record in records] == [1, 2, 3, 4]
    narrative = " ".join(
        str(record["text"])
        for record in records
        if record["content_type"] == "text"
    )
    assert narrative == "Кредитный отчёт Конец"
    assert "Имя" not in narrative


def test_document_csv_contains_unicode_text_and_table_columns(tmp_path):
    records = build_page_records(
        FakePage(),
        3,
        [
            {
                "table_index": 1,
                "strategy": "lines_strict",
                "bbox": [0, 40, 200, 100],
                "rows": [["Имя", "Сумма"], ["Иван", "100"]],
            }
        ],
    )
    output_path = tmp_path / "document.csv"

    assert write_document_csv(records, str(output_path)) == 4

    with open(output_path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["text"] == "Кредитный отчёт"
    assert rows[1]["content_type"] == "table"
    assert rows[1]["column_1"] == "Имя"
    assert rows[1]["column_2"] == "Сумма"


def test_export_job_creates_document_and_both_table_downloads(monkeypatch, tmp_path):
    """One extraction should expose all three useful CSV download formats."""
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"test")
    output_dir = tmp_path / "output"
    result = {
        "pages": 1,
        "tables": [
            {
                "page": 1,
                "table_index": 1,
                "strategy": "lines_strict",
                "rows": [["Имя", "Сумма"], ["Иван", "100"]],
            }
        ],
        "document_records": [
            {
                "page": 1,
                "content_order": 1,
                "content_type": "text",
                "text": "Кредитный отчёт",
                "columns": [],
            },
            {
                "page": 1,
                "content_order": 2,
                "content_type": "table",
                "table_index": 1,
                "row_index": 1,
                "strategy": "lines_strict",
                "text": "",
                "columns": ["Имя", "Сумма"],
            },
        ],
        "strategy_summary": {"lines_strict": 1},
        "used_camelot": False,
        "used_ocr": False,
    }
    monkeypatch.setattr(table_extractor, "extract_tables_from_pdf", lambda _path: result)
    monkeypatch.setenv("PUBLIC_API_URL", "https://converter.example")

    table_extractor.run_table_extraction_job(
        "job-1",
        str(pdf_path),
        str(output_dir),
        "Отчёт.pdf",
    )

    status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "completed"
    assert status["document_row_count"] == 2
    assert status["download_name"] == "Отчёт_document.csv"
    assert status["tables_download_url"].endswith("?kind=tables")
    assert status["archive_download_url"].endswith("?kind=archive")
    assert (output_dir / status["output_filename"]).exists()
    assert (output_dir / status["tables_filename"]).exists()
    assert (output_dir / status["archive_filename"]).exists()


def test_export_job_succeeds_when_pdf_has_text_but_no_tables(monkeypatch, tmp_path):
    """A full-document CSV must not require the source PDF to contain tables."""
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"test")
    output_dir = tmp_path / "output"
    result = {
        "pages": 1,
        "tables": [],
        "document_records": [
            {
                "page": 1,
                "content_order": 1,
                "content_type": "text",
                "text": "Plain document text",
                "columns": [],
            }
        ],
        "strategy_summary": {},
        "used_camelot": False,
        "used_ocr": False,
    }
    monkeypatch.setattr(table_extractor, "extract_tables_from_pdf", lambda _path: result)

    table_extractor.run_table_extraction_job(
        "job-2",
        str(pdf_path),
        str(output_dir),
        "plain.pdf",
    )

    status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "completed"
    assert status["table_count"] == 0
    assert status["tables_download_url"] is None
    assert status["archive_download_url"] is None
