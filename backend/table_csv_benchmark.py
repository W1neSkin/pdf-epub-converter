#!/usr/bin/env python3
"""
Automated benchmark for PDF -> CSV table extraction quality.

What it does:
1) downloads a curated set of public table-heavy PDFs
2) runs the local extraction pipeline
3) writes one CSV per sample
4) writes JSON + Markdown report with quality metrics
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from table_extractor import extract_tables_from_pdf, write_tables_to_single_csv


@dataclass
class Sample:
    name: str
    url: str
    expected_tables: bool = True


SAMPLES: List[Sample] = [
    Sample(
        name="camelot_foo",
        url="https://raw.githubusercontent.com/camelot-dev/camelot/master/docs/_static/pdf/foo.pdf",
    ),
    Sample(
        name="camelot_table_regions",
        url="https://raw.githubusercontent.com/camelot-dev/camelot/master/docs/_static/pdf/table_regions.pdf",
    ),
    Sample(
        name="camelot_table_areas",
        url="https://raw.githubusercontent.com/camelot-dev/camelot/master/docs/_static/pdf/table_areas.pdf",
    ),
    Sample(
        name="camelot_column_separators",
        url="https://raw.githubusercontent.com/camelot-dev/camelot/master/docs/_static/pdf/column_separators.pdf",
    ),
    Sample(
        name="camelot_short_lines",
        url="https://raw.githubusercontent.com/camelot-dev/camelot/master/docs/_static/pdf/short_lines.pdf",
    ),
    Sample(
        name="pdfplumber_background_checks",
        url="https://raw.githubusercontent.com/jsvine/pdfplumber/stable/examples/pdfs/background-checks.pdf",
    ),
]


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=40) as response:  # nosec B310
        destination.write_bytes(response.read())


def _maybe_copy_local_user_pdf(samples_dir: Path) -> List[Path]:
    """Optionally include user's own local PDF when available."""
    candidates = [
        Path(r"E:\Downloads\41542.pdf"),
        Path("/mnt/e/Downloads/41542.pdf"),
    ]
    copied: List[Path] = []
    for candidate in candidates:
        if candidate.exists():
            target = samples_dir / "user_41542.pdf"
            shutil.copy2(candidate, target)
            copied.append(target)
            break
    return copied


def _build_report_rows(results: List[Dict[str, object]]) -> str:
    lines = [
        "# PDF table extraction benchmark",
        "",
        "| Sample | Pages | Tables | Rows | Dominant strategy | Status |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in results:
        lines.append(
            f"| {row['sample']} | {row['pages']} | {row['tables']} | {row['rows']} | "
            f"{row['dominant_strategy']} | {row['status']} |"
        )
    return "\n".join(lines) + "\n"


def run_benchmark(report_dir: Path) -> Dict[str, object]:
    samples_dir = report_dir / "samples"
    csv_dir = report_dir / "csv"
    report_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    benchmark_samples = list(SAMPLES)
    local_pdf = _maybe_copy_local_user_pdf(samples_dir)
    if local_pdf:
        benchmark_samples.append(
            Sample(name="user_41542", url="local://user_41542.pdf", expected_tables=False)
        )

    results: List[Dict[str, object]] = []
    for sample in benchmark_samples:
        sample_pdf = samples_dir / f"{sample.name}.pdf"
        if sample.url.startswith("local://"):
            if not sample_pdf.exists():
                # local copy path already handled above; skip if unavailable
                continue
        elif not sample_pdf.exists():
            _download(sample.url, sample_pdf)

        output = extract_tables_from_pdf(str(sample_pdf))
        tables = output.get("tables", [])
        pages = int(output.get("pages", 0) or 0)
        strategy_summary = output.get("strategy_summary", {})
        dominant_strategy = "-"
        if strategy_summary:
            dominant_strategy = max(strategy_summary, key=strategy_summary.get)

        csv_path = csv_dir / f"{sample.name}.csv"
        status = "ok"
        rows = 0
        try:
            rows = write_tables_to_single_csv(tables, str(csv_path))
        except Exception:
            status = "no_tables"
            if sample.expected_tables:
                status = "needs_tuning"

        results.append(
            {
                "sample": sample.name,
                "pages": pages,
                "tables": len(tables),
                "rows": rows,
                "dominant_strategy": dominant_strategy,
                "status": status,
                "strategy_summary": strategy_summary,
            }
        )

    summary = {
        "total_samples": len(results),
        "ok_samples": sum(1 for row in results if row["status"] == "ok"),
        "needs_tuning_samples": sum(1 for row in results if row["status"] == "needs_tuning"),
        "results": results,
    }

    (report_dir / "benchmark_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "benchmark_report.md").write_text(
        _build_report_rows(results),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run automatic PDF->CSV benchmark")
    parser.add_argument(
        "--report-dir",
        default="backend/table-benchmark",
        help="Directory for downloaded PDFs, CSV outputs, and reports",
    )
    args = parser.parse_args()
    report_dir = Path(args.report_dir)

    # Keep run isolated even when report dir points inside repository.
    temp_root = Path(tempfile.mkdtemp(prefix="table_bench_"))
    temp_report = temp_root / "report"
    summary = run_benchmark(temp_report)

    report_dir.mkdir(parents=True, exist_ok=True)
    for child in temp_report.iterdir():
        target = report_dir / child.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(child), str(target))

    shutil.rmtree(temp_root, ignore_errors=True)
    print(f"Benchmark report saved to: {report_dir}")
    print(
        f"Samples: {summary['total_samples']}, ok: {summary['ok_samples']}, "
        f"needs_tuning: {summary['needs_tuning_samples']}"
    )


if __name__ == "__main__":
    main()
