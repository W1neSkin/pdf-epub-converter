#!/usr/bin/env python3
"""
Generate fixed-layout XHTML pages for EPUB packaging.

The target is visual parity with the source PDF:
- one XHTML page per PDF page
- one full-page image inside each XHTML page
"""

import html
import os
from typing import Any, Dict, List


class HTMLPageGenerator:
    """Build one fixed-layout XHTML file per PDF page."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _build_text_overlay(
        page_data: Dict[str, Any],
        viewport_width: int,
        viewport_height: int,
        page_width: float,
        page_height: float,
    ) -> str:
        """
        Build invisible positioned text boxes so selection matches page image.

        Coordinates come from pdfplumber word boxes in PDF units.
        """
        boxes = page_data.get("text_boxes") or []
        if not boxes or page_width <= 0 or page_height <= 0:
            return ""

        scale_x = viewport_width / page_width
        scale_y = viewport_height / page_height
        # Do not insert formatting whitespace between character spans.
        # Browser selection includes those text nodes and would otherwise copy
        # "Р э г..." instead of the original "Рег...".
        overlay_parts = ['    <div class="text-overlay">']

        for box in boxes:
            raw_text = str(box.get("text") or "")
            if raw_text == "":
                continue
            x0 = float(box.get("x0", 0) or 0)
            x1 = float(box.get("x1", 0) or 0)
            top = float(box.get("top", 0) or 0)
            bottom = float(box.get("bottom", 0) or 0)
            if x1 <= x0 or bottom <= top:
                continue

            left_px = x0 * scale_x
            top_px = top * scale_y
            width_px = max(0.5, (x1 - x0) * scale_x)
            height_px = max(1.0, (bottom - top) * scale_y)
            font_px = max(6.0, height_px * 0.9)

            style = (
                f"left:{left_px:.2f}px;"
                f"top:{top_px:.2f}px;"
                f"width:{width_px:.2f}px;"
                f"height:{height_px:.2f}px;"
                f"font-size:{font_px:.2f}px;"
            )
            classes = "overlay-word"
            if box.get("is_separator"):
                classes += " overlay-separator"
            overlay_parts.append(
                f'<span class="{classes}" style="{style}">{html.escape(raw_text)}</span>'
            )

        overlay_parts.append("</div>\n")
        return "".join(overlay_parts)

    def generate_page_html(self, page_data: Dict[str, Any], output_path: str) -> str:
        """Generate one XHTML page that renders only the source page image."""
        page_num = int(page_data.get("page_number", 0) or 0)
        image_path = page_data.get("image_path")
        if not image_path:
            raise ValueError(
                f"Missing page image for page {page_num}. "
                "Fixed-layout EPUB requires an image for every page."
            )

        page_width = float(page_data.get("width", 0) or 0)
        page_height = float(page_data.get("height", 0) or 0)
        image_width_px = int(page_data.get("image_width_px", 0) or 0)
        image_height_px = int(page_data.get("image_height_px", 0) or 0)
        if image_width_px > 0 and image_height_px > 0:
            # Use the exact rendered bitmap size for best text-overlay alignment.
            viewport_width = image_width_px
            viewport_height = image_height_px
        elif page_width > 0 and page_height > 0:
            # Fallback when bitmap size is unavailable.
            viewport_width = max(600, int(page_width * 2))
            viewport_height = max(800, int(page_height * 2))
        else:
            viewport_width = 1200
            viewport_height = 1696

        image_name = os.path.basename(image_path)
        overlay_html = self._build_text_overlay(
            page_data=page_data,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            page_width=page_width,
            page_height=page_height,
        )

        xhtml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE html>\n"
            "<html xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"en\">\n"
            "<head>\n"
            f"  <title>Page {page_num}</title>\n"
            "  <link rel=\"stylesheet\" type=\"text/css\" href=\"styles.css\"/>\n"
            f"  <meta name=\"viewport\" content=\"width={viewport_width},height={viewport_height}\"/>\n"
            "</head>\n"
            "<body>\n"
            f"  <article class=\"pdf-page fixed-layout-page\" id=\"page-{page_num}\" style=\"width:{viewport_width}px;height:{viewport_height}px;\">\n"
            "    <figure class=\"page-figure fixed-layout-figure\">\n"
            f"      <img class=\"page-image\" src=\"images/{html.escape(image_name)}\" alt=\"Page {page_num}\"/>\n"
            "    </figure>\n"
            f"{overlay_html}"
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
