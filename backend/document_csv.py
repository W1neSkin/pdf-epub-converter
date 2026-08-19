"""Build a flat, ordered CSV representation of PDF text and tables."""

import csv
import os
from typing import Dict, List, Sequence


def _number(value: object) -> float:
    """Return a safe coordinate value from a PDF extraction result."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _inside_bbox(word: Dict[str, object], bbox: Sequence[object]) -> bool:
    """Check the word centre so partially overlapping table words are included."""
    if len(bbox) != 4:
        return False
    center_x = (_number(word.get("x0")) + _number(word.get("x1"))) / 2
    center_y = (_number(word.get("top")) + _number(word.get("bottom"))) / 2
    x0, top, x1, bottom = (_number(value) for value in bbox)
    return x0 <= center_x <= x1 and top <= center_y <= bottom


def _text_records(page: object, table_bboxes: List[Sequence[object]]) -> List[Dict[str, object]]:
    """Group words outside detected tables into readable text lines."""
    extract_words = getattr(page, "extract_words", None)
    if not extract_words:
        return []
    words = extract_words(use_text_flow=True, keep_blank_chars=False) or []
    words = [
        word
        for word in words
        if str(word.get("text") or "").strip()
        and not any(_inside_bbox(word, bbox) for bbox in table_bboxes)
    ]
    words.sort(key=lambda word: (_number(word.get("top")), _number(word.get("x0"))))

    lines: List[Dict[str, object]] = []
    for word in words:
        top = _number(word.get("top"))
        bottom = _number(word.get("bottom"))
        height = max(1.0, bottom - top)
        matching_line = None
        for line in reversed(lines[-3:]):
            tolerance = max(2.0, min(height, _number(line["height"])) * 0.5)
            if abs(top - _number(line["top"])) <= tolerance:
                matching_line = line
                break

        if matching_line is None:
            lines.append(
                {
                    "top": top,
                    "left": _number(word.get("x0")),
                    "height": height,
                    "words": [word],
                }
            )
        else:
            matching_line["words"].append(word)
            matching_line["top"] = min(_number(matching_line["top"]), top)
            matching_line["left"] = min(
                _number(matching_line["left"]),
                _number(word.get("x0")),
            )

    records: List[Dict[str, object]] = []
    for line in lines:
        line_words = sorted(line["words"], key=lambda word: _number(word.get("x0")))
        text = " ".join(str(word.get("text") or "").strip() for word in line_words).strip()
        if text:
            records.append(
                {
                    "content_type": "text",
                    "top": line["top"],
                    "left": line["left"],
                    "text": text,
                    "columns": [],
                }
            )
    return records


def _table_records(tables: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Convert bounded tables into positioned row records."""
    records: List[Dict[str, object]] = []
    for table in tables:
        bbox = table.get("bbox")
        rows = table.get("rows") or []
        if not bbox or len(bbox) != 4 or not rows:
            continue

        top = _number(bbox[1])
        left = _number(bbox[0])
        row_height = max(1.0, (_number(bbox[3]) - top) / len(rows))
        for row_index, row in enumerate(rows, 1):
            records.append(
                {
                    "content_type": "table",
                    "top": top + ((row_index - 1) * row_height),
                    "left": left,
                    "table_index": table.get("table_index", 0),
                    "row_index": row_index,
                    "strategy": table.get("strategy", ""),
                    "text": "",
                    "columns": list(row),
                }
            )
    return records


def build_page_records(
    page: object,
    page_number: int,
    tables: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """Return text and table rows in approximate visual reading order."""
    bounded_tables = [table for table in tables if table.get("bbox")]
    bboxes = [table["bbox"] for table in bounded_tables]
    records = _text_records(page, bboxes) + _table_records(bounded_tables)
    records.sort(key=lambda record: (_number(record.get("top")), _number(record.get("left"))))

    for content_order, record in enumerate(records, 1):
        record["page"] = page_number
        record["content_order"] = content_order
    return records


def build_unpositioned_table_records(tables: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Preserve OCR/fallback table content when page coordinates are unavailable."""
    records: List[Dict[str, object]] = []
    order_by_page: Dict[int, int] = {}
    for table in tables:
        page = int(table.get("page", 0) or 0)
        for row_index, row in enumerate(table.get("rows") or [], 1):
            order_by_page[page] = order_by_page.get(page, 0) + 1
            records.append(
                {
                    "page": page,
                    "content_order": order_by_page[page],
                    "content_type": "table",
                    "table_index": table.get("table_index", 0),
                    "row_index": row_index,
                    "strategy": table.get("strategy", ""),
                    "text": "",
                    "columns": list(row),
                }
            )
    return records


def write_document_csv(records: List[Dict[str, object]], output_path: str) -> int:
    """Write ordered document records and return the exported row count."""
    if not records:
        raise ValueError("No text or tables found in this PDF")

    max_columns = max((len(record.get("columns") or []) for record in records), default=0)
    header = [
        "page",
        "content_order",
        "content_type",
        "table_index",
        "row_index",
        "strategy",
        "text",
        *[f"column_{index}" for index in range(1, max_columns + 1)],
    ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for record in records:
            columns = list(record.get("columns") or [])
            columns.extend([""] * (max_columns - len(columns)))
            writer.writerow(
                [
                    record.get("page", ""),
                    record.get("content_order", ""),
                    record.get("content_type", ""),
                    record.get("table_index", ""),
                    record.get("row_index", ""),
                    record.get("strategy", ""),
                    record.get("text", ""),
                    *columns,
                ]
            )
    return len(records)
