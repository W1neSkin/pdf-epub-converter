import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import table_extractor  # noqa: E402


class _FakePage:
    # Empty chars -> treated as scanned/no text layer.
    chars = []


class _FakePdf:
    def __init__(self):
        self.pages = [_FakePage()]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _empty_candidate(strategy: str) -> dict:
    return {
        "strategy": strategy,
        "tables": [],
        "score": 0.0,
        "fragmented": False,
        "stats": {
            "total_rows": 0,
            "max_columns": 0,
            "non_empty_cells": 0,
            "short_ratio": 0.0,
        },
    }


def test_extract_tables_marks_camelot_usage_when_pdfplumber_empty(monkeypatch):
    monkeypatch.setattr(table_extractor.pdfplumber, "open", lambda _path: _FakePdf())
    monkeypatch.setattr(
        table_extractor,
        "_extract_with_strategy",
        lambda *_args, **_kwargs: _empty_candidate("lines_strict"),
    )
    monkeypatch.setattr(table_extractor, "camelot", object())
    monkeypatch.setattr(
        table_extractor,
        "_extract_with_camelot",
        lambda *_args, **_kwargs: [
            {
                "strategy": "camelot_stream",
                "tables": [{"rows": [["A", "B"], ["1", "2"]], "score": 10.0}],
                "score": 10.0,
                "fragmented": False,
                "stats": {
                    "total_rows": 2,
                    "max_columns": 2,
                    "non_empty_cells": 4,
                    "short_ratio": 0.0,
                },
            }
        ],
    )
    monkeypatch.setattr(table_extractor, "_extract_tables_with_ocr", lambda *_args, **_kwargs: [])

    result = table_extractor.extract_tables_from_pdf("dummy.pdf")
    assert result["used_camelot"] is True
    assert result["used_ocr"] is False
    assert len(result["tables"]) == 1
    assert result["tables"][0]["strategy"] == "camelot_stream"


def test_extract_tables_uses_ocr_when_no_text_layer_and_no_other_tables(monkeypatch):
    monkeypatch.setattr(table_extractor.pdfplumber, "open", lambda _path: _FakePdf())
    monkeypatch.setattr(
        table_extractor,
        "_extract_with_strategy",
        lambda *_args, **_kwargs: _empty_candidate("lines_strict"),
    )
    monkeypatch.setattr(table_extractor, "camelot", None)
    monkeypatch.setattr(
        table_extractor,
        "_extract_tables_with_ocr",
        lambda *_args, **_kwargs: [
            {
                "page": 1,
                "table_index": 1,
                "strategy": "ocr_words_gap",
                "rows": [["A", "B"], ["1", "2"]],
            }
        ],
    )

    result = table_extractor.extract_tables_from_pdf("dummy.pdf")
    assert result["used_camelot"] is False
    assert result["used_ocr"] is True
    assert len(result["tables"]) == 1
    assert result["tables"][0]["strategy"] == "ocr_words_gap"
