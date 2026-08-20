#!/usr/bin/env python3
"""
EPUB generator for reflowable XHTML pages.

The input pages already contain real text nodes. This module only packages
them into a valid EPUB container and keeps optional page figures.
"""

import html
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import List


class EPUBGenerator:
    """Package XHTML pages + images into EPUB 3."""

    def __init__(self) -> None:
        self.epub_id = str(uuid.uuid4())
        self.creation_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_mimetype(self, epub_dir: str) -> None:
        path = os.path.join(epub_dir, "mimetype")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("application/epub+zip")

    def create_container_xml(self, epub_dir: str) -> None:
        meta_inf_dir = os.path.join(epub_dir, "META-INF")
        os.makedirs(meta_inf_dir, exist_ok=True)
        xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n"
            "  <rootfiles>\n"
            "    <rootfile full-path=\"EPUB/content.opf\" media-type=\"application/oebps-package+xml\"/>\n"
            "  </rootfiles>\n"
            "</container>\n"
        )
        with open(os.path.join(meta_inf_dir, "container.xml"), "w", encoding="utf-8") as handle:
            handle.write(xml)

    @staticmethod
    def _media_type(filename: str) -> str:
        lower = filename.lower()
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith(".jpg") or lower.endswith(".jpeg"):
            return "image/jpeg"
        if lower.endswith(".webp"):
            return "image/webp"
        return "application/octet-stream"

    def create_content_opf(
        self,
        epub_dir: str,
        title: str,
        html_files: List[str],
        image_files: List[str],
        language: str = "en",
    ) -> None:
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        os.makedirs(epub_content_dir, exist_ok=True)

        manifest_items: List[str] = []
        spine_items: List[str] = []

        for i, filename in enumerate(html_files, 1):
            item_id = f"page_{i}"
            manifest_items.append(
                f'    <item id="{item_id}" href="{html.escape(filename)}" media-type="application/xhtml+xml"/>'
            )
            spine_items.append(f'    <itemref idref="{item_id}"/>')

        for i, filename in enumerate(image_files, 1):
            item_id = f"img_{i}"
            manifest_items.append(
                f'    <item id="{item_id}" href="images/{html.escape(filename)}" media-type="{self._media_type(filename)}"/>'
            )

        manifest_items.append('    <item id="stylesheet" href="styles.css" media-type="text/css"/>')
        manifest_items.append(
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        )

        escaped_title = html.escape(title or "Converted PDF")
        escaped_language = html.escape(language or "en")
        content_opf = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<package version=\"3.0\" xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"uid\">\n"
            "  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n"
            f"    <dc:identifier id=\"uid\">{self.epub_id}</dc:identifier>\n"
            f"    <dc:title>{escaped_title}</dc:title>\n"
            "    <dc:creator>PDF to EPUB Converter</dc:creator>\n"
            f"    <dc:language>{escaped_language}</dc:language>\n"
            f"    <dc:date>{self.creation_date}</dc:date>\n"
            f"    <meta property=\"dcterms:modified\">{self.creation_date}</meta>\n"
            "    <meta property=\"rendition:layout\">pre-paginated</meta>\n"
            "    <meta property=\"rendition:orientation\">auto</meta>\n"
            "    <meta property=\"rendition:spread\">auto</meta>\n"
            "    <dc:description>Converted from PDF in fixed-layout mode</dc:description>\n"
            "  </metadata>\n"
            "  <manifest>\n"
            f"{chr(10).join(manifest_items)}\n"
            "  </manifest>\n"
            "  <spine>\n"
            f"{chr(10).join(spine_items)}\n"
            "  </spine>\n"
            "</package>\n"
        )

        with open(os.path.join(epub_content_dir, "content.opf"), "w", encoding="utf-8") as handle:
            handle.write(content_opf)

    def create_navigation(self, epub_dir: str, html_files: List[str]) -> None:
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        nav_items = []
        for i, filename in enumerate(html_files, 1):
            nav_items.append(
                f'        <li><a href="{html.escape(filename)}">Page {i}</a></li>'
            )

        nav_xhtml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE html>\n"
            "<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" lang=\"en\">\n"
            "<head>\n"
            "  <title>Table of Contents</title>\n"
            "  <link rel=\"stylesheet\" type=\"text/css\" href=\"styles.css\"/>\n"
            "</head>\n"
            "<body>\n"
            "  <nav epub:type=\"toc\" id=\"toc\">\n"
            "    <h1>Table of Contents</h1>\n"
            "    <ol>\n"
            f"{chr(10).join(nav_items)}\n"
            "    </ol>\n"
            "  </nav>\n"
            "</body>\n"
            "</html>\n"
        )

        with open(os.path.join(epub_content_dir, "nav.xhtml"), "w", encoding="utf-8") as handle:
            handle.write(nav_xhtml)

    def create_stylesheet(self, epub_dir: str) -> None:
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        css = (
            "body {\n"
            "  margin: 0;\n"
            "  padding: 0;\n"
            "  background: #ffffff;\n"
            "}\n"
            ".pdf-page {\n"
            "  margin: 0;\n"
            "  padding: 0;\n"
            "  position: relative;\n"
            "}\n"
            ".fixed-layout-figure {\n"
            "  margin: 0;\n"
            "  padding: 0;\n"
            "  width: 100%;\n"
            "  height: 100%;\n"
            "}\n"
            ".page-figure {\n"
            "  margin: 0;\n"
            "}\n"
            ".page-image,\n"
            ".page-figure img {\n"
            "  display: block;\n"
            "  width: 100%;\n"
            "  height: 100%;\n"
            "  object-fit: fill;\n"
            "  user-select: none;\n"
            "  -webkit-user-select: none;\n"
            "  -webkit-user-drag: none;\n"
            "}\n"
            ".text-overlay {\n"
            "  position: absolute;\n"
            "  left: 0;\n"
            "  top: 0;\n"
            "  width: 100%;\n"
            "  height: 100%;\n"
            "  pointer-events: none;\n"
            "  user-select: none;\n"
            "  -webkit-user-select: none;\n"
            "}\n"
            ".overlay-word {\n"
            "  position: absolute;\n"
            "  display: inline-block;\n"
            "  margin: 0;\n"
            "  padding: 0;\n"
            "  line-height: 1;\n"
            "  /* Preserve real PDF spaces without adding separators between characters. */\n"
            "  white-space: pre;\n"
            "  color: transparent;\n"
            "  -webkit-text-fill-color: transparent;\n"
            "  background: transparent;\n"
            "  cursor: text;\n"
            "  pointer-events: auto;\n"
            "  user-select: text;\n"
            "  -webkit-user-select: text;\n"
            "}\n"
            ".overlay-separator {\n"
            "  pointer-events: none;\n"
            "}\n"
            "nav ol { padding-left: 1.5rem; }\n"
            "nav li { margin: 0.5rem 0; }\n"
        )
        with open(os.path.join(epub_content_dir, "styles.css"), "w", encoding="utf-8") as handle:
            handle.write(css)

    @staticmethod
    def _collect_pages(html_dir: str) -> List[str]:
        files: List[str] = []
        for name in sorted(os.listdir(html_dir)):
            if not name.startswith("page_"):
                continue
            if name.endswith(".xhtml") or name.endswith(".html"):
                files.append(name)
        return files

    @staticmethod
    def _collect_images(image_dir: str) -> List[str]:
        files: List[str] = []
        for name in sorted(os.listdir(image_dir)):
            lower = name.lower()
            if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".webp"):
                files.append(name)
        return files

    def generate_epub(
        self,
        html_dir: str,
        image_dir: str,
        output_filename: str = "converted.epub",
        title: str = "Converted PDF",
        language: str = "en",
    ) -> str:
        """Generate EPUB file from XHTML pages and optional images."""
        page_files = self._collect_pages(html_dir)
        if not page_files:
            raise ValueError("No page XHTML files found")

        image_files = self._collect_images(image_dir)
        temp_dir = tempfile.mkdtemp(prefix="epub_")
        try:
            self.create_mimetype(temp_dir)
            self.create_container_xml(temp_dir)

            epub_content_dir = os.path.join(temp_dir, "EPUB")
            os.makedirs(epub_content_dir, exist_ok=True)
            epub_images_dir = os.path.join(epub_content_dir, "images")
            os.makedirs(epub_images_dir, exist_ok=True)

            copied_pages: List[str] = []
            for page_file in page_files:
                src = os.path.join(html_dir, page_file)
                dest_name = page_file[:-5] + ".xhtml" if page_file.endswith(".html") else page_file
                dest = os.path.join(epub_content_dir, dest_name)
                shutil.copy2(src, dest)
                copied_pages.append(dest_name)

            copied_images: List[str] = []
            for image_file in image_files:
                src = os.path.join(image_dir, image_file)
                dest = os.path.join(epub_images_dir, image_file)
                if not os.path.isfile(src):
                    continue
                shutil.copy2(src, dest)
                copied_images.append(image_file)

            self.create_content_opf(
                epub_dir=temp_dir,
                title=title,
                html_files=copied_pages,
                image_files=copied_images,
                language=language,
            )
            self.create_navigation(temp_dir, copied_pages)
            self.create_stylesheet(temp_dir)

            if os.path.exists(output_filename):
                os.remove(output_filename)

            with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(
                    os.path.join(temp_dir, "mimetype"),
                    "mimetype",
                    compress_type=zipfile.ZIP_STORED,
                )
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        if file_name == "mimetype":
                            continue
                        file_path = os.path.join(root, file_name)
                        archive_path = os.path.relpath(file_path, temp_dir)
                        archive.write(file_path, archive_path)
            return output_filename
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    print("EPUBGenerator is used by conversion_jobs.py")


if __name__ == "__main__":
    main()
