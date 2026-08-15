#!/usr/bin/env python3
"""
Alternative PDF parser used by the conversion job.

Goal:
- Extract real Unicode text for reflowable EPUB output.
- Render page images only when needed (no text or image-heavy page).
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional

import PyPDF2
import pdfplumber
from pdf2image import convert_from_path


ProgressCallback = Optional[Callable[[int, str, int, int], None]]


class AlternativePDFParser:
    """PDF parser that prefers text extraction over full-page rasterization."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _word_count(text: str) -> int:
        return len([token for token in text.split() if token.strip()])

    def extract_text_pdfplumber(self, pdf_path: str, on_progress: ProgressCallback = None) -> List[Dict[str, Any]]:
        """Extract page text and basic page facts using pdfplumber."""
        pages_data: List[Dict[str, Any]] = []
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                # layout=True preserves line breaks better for forms/documents.
                text = (page.extract_text(layout=True) or page.extract_text() or "").strip()
                pages_data.append(
                    {
                        "page_number": page_num,
                        "text": text,
                        "word_count": self._word_count(text),
                        "width": float(getattr(page, "width", 0) or 0),
                        "height": float(getattr(page, "height", 0) or 0),
                        "has_text": bool(text),
                        # If the PDF page contains images, keep a rendered image as figure.
                        "has_images": bool(getattr(page, "images", None)),
                    }
                )

                if on_progress and total:
                    percent = 10 + int(20 * page_num / total)
                    on_progress(
                        percent,
                        f"Extracting text from page {page_num} of {total}",
                        page_num,
                        total,
                    )
        return pages_data

    def extract_text_pypdf2(self, pdf_path: str, pages_data: List[Dict[str, Any]]) -> None:
        """Fill empty pages with a lightweight PyPDF2 fallback."""
        if not pages_data:
            return
        with open(pdf_path, "rb") as handle:
            reader = PyPDF2.PdfReader(handle)
            for page_data in pages_data:
                if page_data.get("has_text"):
                    continue
                page_index = page_data["page_number"] - 1
                if page_index < 0 or page_index >= len(reader.pages):
                    continue
                text = (reader.pages[page_index].extract_text() or "").strip()
                if not text:
                    continue
                page_data["text"] = text
                page_data["word_count"] = self._word_count(text)
                page_data["has_text"] = True

    def convert_to_images(
        self,
        pdf_path: str,
        output_dir: str,
        page_numbers: List[int],
        on_progress: ProgressCallback = None,
    ) -> Dict[int, str]:
        """
        Render selected pages to PNG one-by-one.

        Rendering all pages at once can exceed free-host memory on long PDFs.
        """
        image_paths: Dict[int, str] = {}
        if not page_numbers:
            return image_paths

        os.makedirs(output_dir, exist_ok=True)
        selected = sorted(set(page_numbers))
        total = len(selected)
        if on_progress:
            on_progress(32, "Rendering page images...", 0, total)

        for i, page_number in enumerate(selected, 1):
            images = convert_from_path(
                pdf_path,
                dpi=120,
                first_page=page_number,
                last_page=page_number,
            )
            if not images:
                continue

            image_filename = f"page_{page_number:03d}.png"
            image_path = os.path.join(output_dir, image_filename)
            images[0].save(image_path, "PNG")
            images[0].close()
            image_paths[page_number] = image_path

            if on_progress:
                percent = 32 + int(20 * i / total)
                on_progress(
                    percent,
                    f"Saving page image {i} of {total}",
                    i,
                    total,
                )
        return image_paths

    def parse_pdf(self, pdf_path: str, output_dir: str = "alternative_output", on_progress: ProgressCallback = None) -> Dict[str, Any]:
        """Parse PDF and return normalized per-page data for the EPUB pipeline."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pages_data = self.extract_text_pdfplumber(pdf_path, on_progress=on_progress)
        # Some PDFs expose text only via fallback extraction.
        self.extract_text_pypdf2(pdf_path, pages_data)

        # Render full-page image only when text is absent or page has image resources.
        page_numbers_for_images = [
            page["page_number"]
            for page in pages_data
            if (not page.get("has_text")) or page.get("has_images")
        ]
        image_map = self.convert_to_images(
            pdf_path=pdf_path,
            output_dir=output_dir,
            page_numbers=page_numbers_for_images,
            on_progress=on_progress,
        )

        for page in pages_data:
            image_path = image_map.get(page["page_number"])
            if image_path:
                page["image_path"] = image_path

        all_text = "\n\n".join(page.get("text", "") for page in pages_data if page.get("text"))
        total_words = sum(int(page.get("word_count", 0) or 0) for page in pages_data)
        methods = ["pdfplumber"]
        if any(page.get("has_text") for page in pages_data):
            methods.append("PyPDF2-fallback")
        if image_map:
            methods.append("pdf2image")

        return {
            "pdf_path": pdf_path,
            "page_count": len(pages_data),
            "pages": pages_data,
            "total_text": all_text,
            "total_words": total_words,
            "output_directory": output_dir,
            "methods_used": methods,
        }

    def save_results(self, results: Dict[str, Any], output_file: str = "alternative_results.json") -> None:
        """Save a lightweight debug report and full extracted text."""
        clean_results = dict(results)
        clean_results["pages"] = [
            {
                "page_number": page.get("page_number"),
                "text_preview": (page.get("text", "")[:300] + "...") if len(page.get("text", "")) > 300 else page.get("text", ""),
                "word_count": page.get("word_count", 0),
                "image_path": page.get("image_path"),
                "has_text": page.get("has_text", False),
                "has_images": page.get("has_images", False),
                "width": page.get("width"),
                "height": page.get("height"),
            }
            for page in results.get("pages", [])
        ]

        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(clean_results, handle, indent=2, ensure_ascii=False)

        text_file = output_file.replace(".json", ".txt")
        with open(text_file, "w", encoding="utf-8") as handle:
            handle.write(results.get("total_text", ""))


def main() -> None:
    parser = AlternativePDFParser()
    pdf_file = "sample1.pdf"
    if not os.path.exists(pdf_file):
        print(f"PDF file '{pdf_file}' not found")
        return
    results = parser.parse_pdf(pdf_file)
    parser.save_results(results)
    print(f"Pages: {results['page_count']}, words: {results['total_words']}")


if __name__ == "__main__":
    main()
