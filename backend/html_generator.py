#!/usr/bin/env python3
"""
Generate simple reflowable XHTML pages for EPUB packaging.

This generator intentionally writes real text nodes (<p>...</p>) instead of
invisible overlay spans. It keeps text selectable in any EPUB reader.
"""

import html
import os
import re
from typing import Any, Dict, List


class HTMLPageGenerator:
    """Build one XHTML file per PDF page from parsed page data."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        """
        Split extracted text into readable paragraphs.

        Many form-like PDFs place one phrase per line; we keep line granularity
        instead of aggressively merging all lines into one block.
        """
        normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []

        chunks = re.split(r"\n\s*\n", normalized)
        paragraphs: List[str] = []
        for chunk in chunks:
            lines = [line.strip() for line in chunk.split("\n") if line.strip()]
            paragraphs.extend(lines)
        return paragraphs

    def generate_page_html(self, page_data: Dict[str, Any], output_path: str) -> str:
        """Generate one XHTML page with selectable text and optional figure image."""
        page_num = int(page_data.get("page_number", 0) or 0)
        text = page_data.get("text", "") or ""
        image_path = page_data.get("image_path")
        paragraphs = self._split_paragraphs(text)

        text_html = ""
        if paragraphs:
            lines = []
            for paragraph in paragraphs:
                # Escape every paragraph to keep valid XHTML and preserve Unicode.
                lines.append(f"        <p>{html.escape(paragraph)}</p>")
            text_html = "\n".join(lines)
        else:
            text_html = '        <p class="empty-text">No extractable text on this page.</p>'

        figure_html = ""
        if image_path:
            image_name = os.path.basename(image_path)
            figure_html = (
                "      <figure class=\"page-figure\">\n"
                f"        <img src=\"images/{html.escape(image_name)}\" alt=\"Page {page_num} image\" />\n"
                "      </figure>\n"
            )

        xhtml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE html>\n"
            "<html xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"en\">\n"
            "<head>\n"
            f"  <title>Page {page_num}</title>\n"
            "  <link rel=\"stylesheet\" type=\"text/css\" href=\"styles.css\"/>\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"/>\n"
            "</head>\n"
            "<body>\n"
            f"  <article class=\"pdf-page\" id=\"page-{page_num}\">\n"
            f"    <h2 class=\"page-title\">Page {page_num}</h2>\n"
            "    <section class=\"page-text\">\n"
            f"{text_html}\n"
            "    </section>\n"
            f"{figure_html}"
            "  </article>\n"
            "</body>\n"
            "</html>\n"
        )

        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(xhtml)
        return output_path

    def generate_html_pages(self, pages_data: List[Dict[str, Any]], output_dir: str) -> List[str]:
        """Generate all per-page XHTML files and return their absolute paths."""
        if not isinstance(pages_data, list) or not pages_data:
            raise ValueError("No parsed pages were provided for XHTML generation")

        os.makedirs(output_dir, exist_ok=True)
        html_files: List[str] = []
        for page_data in pages_data:
            page_num = int(page_data.get("page_number", len(html_files) + 1))
            output_path = os.path.join(output_dir, f"page_{page_num:03d}.xhtml")
            html_files.append(self.generate_page_html(page_data, output_path))
        return html_files


def main() -> None:
    print("HTMLPageGenerator is used by conversion_jobs.py")


if __name__ == "__main__":
    main()
