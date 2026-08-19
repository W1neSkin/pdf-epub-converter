#!/usr/bin/env python3
"""
Alternative PDF parser used by the conversion job.

Goal:
- Keep page order and page count exactly as in the source PDF.
- Render a full-page image for every page for fixed-layout EPUB output.
- Still extract plain text for metadata/debug purposes.
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional

import PyPDF2
import pdfplumber
from pdf2image import convert_from_path


ProgressCallback = Optional[Callable[[int, str, int, int], None]]


class AlternativePDFParser:
    """PDF parser that outputs strict one-image-per-page data."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _word_count(text: str) -> int:
        return len([token for token in text.split() if token.strip()])

    @staticmethod
    def _extract_text_boxes(page: Any) -> List[Dict[str, Any]]:
        """
        Extract positioned characters plus real word/line separators.

        Coordinates are kept in PDF page units (points):
        - x0/x1 from left
        - top/bottom from top
        """
        words = page.extract_words(return_chars=True)
        boxes: List[Dict[str, Any]] = []

        for word_index, word in enumerate(words):
            for char in word.get("chars", []):
                text = str(char.get("text") or "")
                x0 = float(char.get("x0", 0) or 0)
                x1 = float(char.get("x1", 0) or 0)
                top = float(char.get("top", 0) or 0)
                bottom = float(char.get("bottom", 0) or 0)
                if text and x1 > x0 and bottom > top:
                    boxes.append(
                        {
                            "text": text,
                            "x0": x0,
                            "x1": x1,
                            "top": top,
                            "bottom": bottom,
                        }
                    )

            if word_index == len(words) - 1:
                continue

            next_word = words[word_index + 1]
            top = float(word.get("top", 0) or 0)
            bottom = float(word.get("bottom", 0) or 0)
            next_top = float(next_word.get("top", 0) or 0)
            next_bottom = float(next_word.get("bottom", 0) or 0)
            overlap = min(bottom, next_bottom) - max(top, next_top)
            same_line = overlap >= min(bottom - top, next_bottom - next_top) * 0.5

            # PDFs commonly omit whitespace glyphs. Add only separators that
            # pdfplumber inferred between its words, never between characters.
            x0 = float(word.get("x1", 0) or 0)
            next_x0 = float(next_word.get("x0", x0) or x0)
            boxes.append(
                {
                    "text": " " if same_line else "\n",
                    "x0": x0,
                    "x1": max(x0 + 0.5, next_x0) if same_line else x0 + 0.5,
                    "top": top,
                    "bottom": bottom,
                }
            )

        return boxes

    def extract_text_pdfplumber(self, pdf_path: str, on_progress: ProgressCallback = None) -> List[Dict[str, Any]]:
        """Extract page text and basic page facts using pdfplumber."""
        pages_data: List[Dict[str, Any]] = []
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                # layout=True preserves line breaks better for forms/documents.
                text = (page.extract_text(layout=True) or page.extract_text() or "").strip()
                text_boxes = self._extract_text_boxes(page)
                pages_data.append(
                    {
                        "page_number": page_num,
                        "text": text,
                        "word_count": self._word_count(text),
                        "text_boxes": text_boxes,
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
    ) -> Dict[int, Dict[str, Any]]:
        """
        Render selected pages to PNG one-by-one.

        Rendering all pages at once can exceed free-host memory on long PDFs.
        """
        image_paths: Dict[int, Dict[str, Any]] = {}
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
                dpi=150,
                first_page=page_number,
                last_page=page_number,
            )
            if not images:
                continue

            image_filename = f"page_{page_number:03d}.png"
            image_path = os.path.join(output_dir, image_filename)
            image_obj = images[0]
            image_obj.save(image_path, "PNG")
            image_obj.close()
            image_paths[page_number] = {
                "path": image_path,
                "width_px": int(getattr(image_obj, "width", 0) or 0),
                "height_px": int(getattr(image_obj, "height", 0) or 0),
            }

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

        # Strict visual mode: every PDF page must have an image in the EPUB.
        page_numbers_for_images = [page["page_number"] for page in pages_data]
        image_map = self.convert_to_images(
            pdf_path=pdf_path,
            output_dir=output_dir,
            page_numbers=page_numbers_for_images,
            on_progress=on_progress,
        )

        missing_pages = [n for n in page_numbers_for_images if n not in image_map]
        if missing_pages:
            missing_text = ", ".join(str(n) for n in missing_pages[:10])
            if len(missing_pages) > 10:
                missing_text += ", ..."
            raise RuntimeError(
                f"Could not render page image(s): {missing_text}. "
                "Cannot build 1:1 visual EPUB without page images."
            )

        for page in pages_data:
            image_info = image_map.get(page["page_number"])
            if image_info:
                page["image_path"] = image_info.get("path")
                page["image_width_px"] = image_info.get("width_px")
                page["image_height_px"] = image_info.get("height_px")

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
