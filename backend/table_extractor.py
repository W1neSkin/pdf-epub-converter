"""
PDF table extraction helpers for CSV export.

Pipeline order:
1) pdfplumber multi-strategy extraction (default)
2) Camelot fallback for hard digital layouts (optional dependency)
3) OCR fallback for scanned PDFs with no text layer (optional dependency)
"""

import csv
import json
import logging
import os
import re
from collections import Counter
from statistics import median
from typing import Any, Dict, List, Tuple

import pdfplumber
from pdf2image import convert_from_path

try:
    import camelot  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    camelot = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None

logger = logging.getLogger(__name__)

# Multiple profiles because real PDFs vary a lot.
TABLE_STRATEGIES: List[Tuple[str, Dict[str, object]]] = [
    (
        "lines_strict",
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 4,
            "snap_tolerance": 2,
            "join_tolerance": 2,
        },
    ),
    (
        "lines_relaxed",
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 8,
            "snap_tolerance": 4,
            "join_tolerance": 4,
        },
    ),
    (
        "text_balanced",
        {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "min_words_vertical": 2,
            "min_words_horizontal": 1,
            "snap_tolerance": 3,
            "join_tolerance": 3,
        },
    ),
    (
        "text_loose",
        {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
            "snap_tolerance": 6,
            "join_tolerance": 6,
        },
    ),
]

CAMELOT_FLAVORS: Tuple[str, ...] = ("stream", "lattice")
OCR_LANG = os.getenv("TABLE_OCR_LANG", "eng+rus")
OCR_MIN_CONFIDENCE = int(os.getenv("TABLE_OCR_MIN_CONFIDENCE", "35"))
OCR_ROW_TOLERANCE = int(os.getenv("TABLE_OCR_ROW_TOLERANCE", "12"))
OCR_FORCE = os.getenv("TABLE_OCR_FORCE", "false").lower() == "true"
OCR_TEXT_LAYER_RATIO_THRESHOLD = float(os.getenv("TABLE_OCR_TEXT_LAYER_RATIO_THRESHOLD", "0.25"))


def _status_path(output_dir: str) -> str:
    return os.path.join(output_dir, "status.json")


def write_status(output_dir: str, **fields: object) -> None:
    """
    Merge fields into status.json for /api/status polling.

    Local copy avoids importing conversion_jobs (and unrelated side-effects).
    """
    os.makedirs(output_dir, exist_ok=True)
    path = _status_path(output_dir)
    current: Dict[str, object] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                current = json.load(handle)
        except Exception:
            current = {}
    current.update(fields)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(current, handle)


def _clean_cell(value: object) -> str:
    """Normalize raw PDF cell text for stable CSV output."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _normalize_rows(raw_table: List[List[object]]) -> List[List[str]]:
    """Drop empty rows and normalize all cells to text."""
    rows: List[List[str]] = []
    for raw_row in raw_table or []:
        if not raw_row:
            continue
        row = [_clean_cell(cell) for cell in raw_row]
        if any(cell for cell in row):
            rows.append(row)
    return rows


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _table_score(rows: List[List[str]]) -> float:
    """Score one table candidate. Higher means more likely useful table."""
    if not rows:
        return -1.0
    row_count = len(rows)
    col_count = max((len(row) for row in rows), default=0)
    if row_count < 2 or col_count < 2:
        return -1.0

    non_empty = sum(1 for row in rows for cell in row if cell)
    cells_total = max(1, row_count * col_count)
    fill_ratio = non_empty / cells_total

    # Prefer denser, larger tables but keep simple.
    short_cells = sum(1 for row in rows for cell in row if cell and len(cell) <= 2)
    short_ratio = short_cells / max(1, non_empty)

    score = float(non_empty) + (row_count * 1.2) + (col_count * 1.8)
    score -= short_ratio * non_empty * 1.7
    score -= max(0, col_count - 12) * row_count * 0.8

    if col_count > 8 and short_ratio > 0.10:
        # Penalize heavily fragmented text-mode outputs.
        score *= 0.35
    if fill_ratio < 0.22:
        score *= 0.5
    return score


def _build_candidate(strategy_name: str, raw_tables: List[List[List[object]]]) -> Dict[str, object]:
    """Normalize/scoring helper shared by pdfplumber, Camelot and OCR paths."""
    normalized_tables: List[Dict[str, object]] = []
    strategy_score = 0.0
    non_empty_cells = 0
    short_cells = 0
    max_columns = 0
    total_rows = 0

    for raw_table in raw_tables:
        rows = _normalize_rows(raw_table)
        score = _table_score(rows)
        if score <= 0:
            continue
        row_count = len(rows)
        col_count = max((len(row) for row in rows), default=0)
        max_columns = max(max_columns, col_count)
        total_rows += row_count
        row_non_empty = sum(1 for row in rows for cell in row if cell)
        non_empty_cells += row_non_empty
        short_cells += sum(1 for row in rows for cell in row if cell and len(cell) <= 2)
        normalized_tables.append({"rows": rows, "score": score})
        strategy_score += score

    short_ratio = short_cells / max(1, non_empty_cells)
    fragmented = (
        max_columns >= 16
        or short_ratio >= 0.35
        or (max_columns >= 10 and total_rows >= 20 and short_ratio >= 0.10)
    )

    return {
        "strategy": strategy_name,
        "tables": normalized_tables,
        "score": strategy_score,
        "fragmented": fragmented,
        "stats": {
            "total_rows": total_rows,
            "max_columns": max_columns,
            "non_empty_cells": non_empty_cells,
            "short_ratio": round(short_ratio, 4),
        },
    }


def _extract_with_strategy(page: pdfplumber.page.Page, strategy_name: str, settings: Dict[str, object]) -> Dict[str, object]:
    """Extract and score tables on one page with a specific pdfplumber profile."""
    raw_tables = page.extract_tables(table_settings=settings) or []
    return _build_candidate(strategy_name, raw_tables)


def _extract_with_camelot(pdf_path: str, page_number: int) -> List[Dict[str, object]]:
    """
    Extract candidate tables via Camelot as fallback.

    Camelot is optional: if dependency/backend is unavailable, we return [].
    """
    if camelot is None:
        return []

    candidates: List[Dict[str, object]] = []
    for flavor in CAMELOT_FLAVORS:
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages=str(page_number),
                flavor=flavor,
                suppress_stdout=True,
            )
        except Exception as exc:
            logger.debug("Camelot %s failed on page %s: %s", flavor, page_number, exc)
            continue

        raw_tables: List[List[List[object]]] = []
        for table in tables:
            try:
                # Camelot table.df is a pandas DataFrame.
                raw_rows = table.df.fillna("").values.tolist()
            except Exception:
                continue
            raw_tables.append(raw_rows)

        candidates.append(_build_candidate(f"camelot_{flavor}", raw_tables))
    return candidates


def _rows_from_ocr_data(ocr_data: Dict[str, List[object]]) -> List[List[str]]:
    """Convert OCR word boxes into rough table rows using row + gap clustering."""
    texts = list(ocr_data.get("text") or [])
    confs = list(ocr_data.get("conf") or [])
    lefts = list(ocr_data.get("left") or [])
    tops = list(ocr_data.get("top") or [])
    widths = list(ocr_data.get("width") or [])
    heights = list(ocr_data.get("height") or [])

    tokens: List[Dict[str, object]] = []
    for i, raw_text in enumerate(texts):
        text = _clean_cell(raw_text)
        if not text:
            continue
        conf = _safe_float(confs[i] if i < len(confs) else 0, default=0)
        if conf < OCR_MIN_CONFIDENCE:
            continue
        left = int(_safe_float(lefts[i] if i < len(lefts) else 0))
        top = int(_safe_float(tops[i] if i < len(tops) else 0))
        width = int(_safe_float(widths[i] if i < len(widths) else 0))
        height = int(_safe_float(heights[i] if i < len(heights) else 0))
        if width <= 0 or height <= 0:
            continue
        tokens.append(
            {
                "text": text,
                "left": left,
                "right": left + width,
                "top": top,
                "height": height,
                "center_y": top + (height / 2.0),
            }
        )

    if not tokens:
        return []

    tokens.sort(key=lambda item: (float(item["center_y"]), int(item["left"])))
    row_groups: List[Dict[str, object]] = []
    for token in tokens:
        token_center_y = float(token["center_y"])
        matched_group = None
        for group in row_groups:
            if abs(token_center_y - float(group["center_y"])) <= OCR_ROW_TOLERANCE:
                matched_group = group
                break
        if matched_group is None:
            row_groups.append({"center_y": token_center_y, "tokens": [token]})
        else:
            matched_group["tokens"].append(token)
            matched_group["center_y"] = (
                float(matched_group["center_y"]) * 0.8 + token_center_y * 0.2
            )

    rows: List[List[str]] = []
    for group in row_groups:
        words = sorted(group["tokens"], key=lambda item: int(item["left"]))
        if not words:
            continue
        heights_for_row = [max(1, int(word["height"])) for word in words]
        gap_threshold = max(18.0, median(heights_for_row) * 1.6)

        cells: List[str] = []
        current_text = str(words[0]["text"])
        previous_right = int(words[0]["right"])
        for word in words[1:]:
            gap = int(word["left"]) - previous_right
            if gap > gap_threshold:
                if current_text.strip():
                    cells.append(current_text.strip())
                current_text = str(word["text"])
            else:
                current_text = f"{current_text} {word['text']}".strip()
            previous_right = max(previous_right, int(word["right"]))
        if current_text.strip():
            cells.append(current_text.strip())
        if cells:
            rows.append(cells)
    return rows


def _has_tesseract_binary() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _extract_tables_with_ocr(pdf_path: str, page_count: int) -> List[Dict[str, object]]:
    """
    OCR fallback for scanned PDFs without a text layer.

    Output is heuristic and should only run when regular extraction fails.
    """
    if pytesseract is None or not _has_tesseract_binary():
        return []

    extracted: List[Dict[str, object]] = []
    language_candidates = [OCR_LANG, "eng", "rus"]
    # Keep order but remove duplicates/empties.
    language_candidates = [lang for i, lang in enumerate(language_candidates) if lang and lang not in language_candidates[:i]]

    for page_number in range(1, page_count + 1):
        try:
            images = convert_from_path(
                pdf_path,
                dpi=220,
                first_page=page_number,
                last_page=page_number,
            )
        except Exception as exc:
            logger.debug("OCR render failed on page %s: %s", page_number, exc)
            continue
        if not images:
            continue

        image = images[0]
        ocr_data = None
        for lang in language_candidates:
            try:
                ocr_data = pytesseract.image_to_data(
                    image,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                )
                break
            except Exception:
                continue

        for extra_image in images:
            extra_image.close()

        if not ocr_data:
            continue

        rows = _rows_from_ocr_data(ocr_data)
        score = _table_score(rows)
        if score <= 0:
            continue
        extracted.append(
            {
                "page": page_number,
                "table_index": 1,
                "strategy": "ocr_words_gap",
                "rows": rows,
            }
        )
    return extracted


def _select_best_candidate(candidates: List[Dict[str, object]]) -> Dict[str, object] | None:
    """Choose best strategy with bias toward non-fragmented line-based tables."""
    if not candidates:
        return None

    with_tables = [candidate for candidate in candidates if candidate["tables"]]
    if not with_tables:
        return max(candidates, key=lambda item: item["score"], default=None)

    line_candidates = [
        candidate
        for candidate in with_tables
        if candidate["strategy"].startswith("lines") and not candidate.get("fragmented")
    ]
    non_fragmented = [candidate for candidate in with_tables if not candidate.get("fragmented")]

    if line_candidates:
        best_line = max(line_candidates, key=lambda item: item["score"])
        best_non_line = max(
            [
                candidate
                for candidate in non_fragmented
                if not candidate["strategy"].startswith("lines")
            ],
            key=lambda item: item["score"],
            default=None,
        )
        # Prefer line strategy unless non-line is dramatically better.
        if best_non_line and best_non_line["score"] > best_line["score"] * 2.5:
            return best_non_line
        return best_line

    if non_fragmented:
        return max(non_fragmented, key=lambda item: item["score"])
    return max(with_tables, key=lambda item: item["score"])


def extract_tables_from_pdf(pdf_path: str) -> Dict[str, object]:
    """
    Extract tables from a PDF using several strategy profiles.

    For each page:
    1) run pdfplumber profiles
    2) if empty, try Camelot
    3) if still empty for full document and likely scanned, try OCR fallback
    """
    extracted: List[Dict[str, object]] = []
    page_count = 0
    diagnostics: List[Dict[str, object]] = []
    text_layer_pages = 0
    used_camelot = False
    used_ocr = False

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages, 1):
            if getattr(page, "chars", None):
                text_layer_pages += 1
            candidates = [
                _extract_with_strategy(page, strategy_name, settings)
                for strategy_name, settings in TABLE_STRATEGIES
            ]

            # If pdfplumber found nothing, try Camelot fallback for this page.
            best = _select_best_candidate(candidates)
            if (not best or best["score"] <= 0) and camelot is not None:
                camelot_candidates = _extract_with_camelot(pdf_path, page_index)
                if camelot_candidates:
                    used_camelot = True
                    candidates.extend(camelot_candidates)

            best = _select_best_candidate(candidates)

            diagnostics.append(
                {
                    "page": page_index,
                    "scores": {item["strategy"]: round(float(item["score"]), 2) for item in candidates},
                    "selected_strategy": best["strategy"] if best else None,
                    "selected_tables": len(best["tables"]) if best else 0,
                    "fragmented": best.get("fragmented") if best else None,
                }
            )

            if not best or best["score"] <= 0:
                continue

            for table_index, table_data in enumerate(best["tables"], 1):
                extracted.append(
                    {
                        "page": page_index,
                        "table_index": table_index,
                        "strategy": best["strategy"],
                        "rows": table_data["rows"],
                    }
                )

    text_layer_ratio = text_layer_pages / max(1, page_count)
    should_try_ocr = (not extracted) and (OCR_FORCE or text_layer_ratio < OCR_TEXT_LAYER_RATIO_THRESHOLD)
    if should_try_ocr:
        ocr_tables = _extract_tables_with_ocr(pdf_path, page_count)
        if ocr_tables:
            used_ocr = True
            extracted.extend(ocr_tables)
            diagnostics.append(
                {
                    "page": "ocr_fallback",
                    "scores": {},
                    "selected_strategy": "ocr_words_gap",
                    "selected_tables": len(ocr_tables),
                    "fragmented": False,
                }
            )

    strategy_counter = Counter(table.get("strategy") for table in extracted if table.get("strategy"))
    strategy_summary = dict(strategy_counter)
    return {
        "pages": page_count,
        "tables": extracted,
        "strategy_summary": strategy_summary,
        "diagnostics": diagnostics,
        "used_camelot": used_camelot,
        "used_ocr": used_ocr,
        "text_layer_pages": text_layer_pages,
        "text_layer_ratio": round(text_layer_ratio, 4),
    }


def write_tables_to_single_csv(tables: List[Dict[str, object]], output_path: str) -> int:
    """Write all extracted tables to one CSV file and return row count."""
    if not tables:
        raise ValueError("No tables found in this PDF")

    max_columns = 0
    for table in tables:
        for row in table.get("rows", []):
            max_columns = max(max_columns, len(row))

    if max_columns == 0:
        raise ValueError("No table rows found in this PDF")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    total_rows = 0
    with open(output_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        header = ["page", "table_index", "row_index", "strategy"] + [f"column_{i}" for i in range(1, max_columns + 1)]
        writer.writerow(header)

        for table in tables:
            page = table.get("page", 0)
            table_index = table.get("table_index", 0)
            strategy = table.get("strategy", "")
            for row_index, row in enumerate(table.get("rows", []), 1):
                padded = row + ([""] * (max_columns - len(row)))
                writer.writerow([page, table_index, row_index, strategy, *padded])
                total_rows += 1

    return total_rows


def run_table_extraction_job(
    conversion_id: str,
    pdf_path: str,
    output_dir: str,
    original_filename: str,
) -> None:
    """Background job: extract tables from PDF and save one CSV file."""
    try:
        write_status(
            output_dir,
            status="processing",
            progress=15,
            message="Reading PDF structure...",
        )

        result = extract_tables_from_pdf(pdf_path)
        page_count = int(result.get("pages", 0) or 0)
        tables = result.get("tables", [])
        strategy_summary = result.get("strategy_summary", {})
        used_camelot = bool(result.get("used_camelot"))
        used_ocr = bool(result.get("used_ocr"))

        write_status(
            output_dir,
            status="processing",
            progress=70,
            message="Building CSV file...",
            pages=page_count,
            table_count=len(tables),
            strategy_summary=strategy_summary,
            used_camelot=used_camelot,
            used_ocr=used_ocr,
        )

        csv_path = os.path.join(output_dir, f"{conversion_id}.csv")
        total_rows = write_tables_to_single_csv(tables, csv_path)

        gateway = os.getenv(
            "PUBLIC_API_URL",
            "https://pdf-converter-api-gateway.onrender.com",
        )
        source_name = os.path.splitext(original_filename or "tables")[0]
        download_name = f"{source_name}_tables.csv"
        completion_message = "CSV is ready"
        if used_ocr:
            completion_message = "CSV is ready (OCR fallback used)"
        elif used_camelot:
            completion_message = "CSV is ready (Camelot fallback used)"
        write_status(
            output_dir,
            status="completed",
            progress=100,
            message=completion_message,
            pages=page_count,
            table_count=len(tables),
            row_count=total_rows,
            strategy_summary=strategy_summary,
            used_camelot=used_camelot,
            used_ocr=used_ocr,
            file_size=os.path.getsize(csv_path),
            download_url=f"{gateway}/api/download/{conversion_id}",
            output_kind="csv",
            output_filename=f"{conversion_id}.csv",
            output_mime="text/csv",
            download_name=download_name,
        )
        logger.info(
            "Table extraction %s completed: %s tables, %s rows, strategies=%s, camelot=%s, ocr=%s",
            conversion_id,
            len(tables),
            total_rows,
            strategy_summary,
            used_camelot,
            used_ocr,
        )
    except Exception as exc:
        logger.error("Table extraction %s failed: %s", conversion_id, exc)
        write_status(
            output_dir,
            status="failed",
            progress=0,
            message=str(exc),
        )
    finally:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
