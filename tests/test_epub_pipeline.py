import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from epub_generator import EPUBGenerator  # noqa: E402
from html_generator import HTMLPageGenerator  # noqa: E402


def test_epub_contains_real_text_and_valid_zip_structure():
    """
    Regression test for the old overlay bug:
    text used to live in data-text attributes of empty spans.
    """
    with tempfile.TemporaryDirectory(prefix="epub_pipeline_test_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        image_path = tmp_path / "page_001.png"

        # Small placeholder image to verify image manifest/copy logic.
        Image.new("RGB", (64, 64), color=(240, 240, 240)).save(image_path)

        page_text = "Регистрационный знак\nY4K8722D9MB308663"
        pages_data = [
            {
                "page_number": 1,
                "text": page_text,
                "word_count": 2,
                "image_path": str(image_path),
                "width": 595.0,
                "height": 842.0,
                "text_boxes": [
                    {
                        "text": "Регистрационный",
                        "x0": 50.0,
                        "x1": 180.0,
                        "top": 70.0,
                        "bottom": 85.0,
                    },
                    {
                        "text": "знак",
                        "x0": 190.0,
                        "x1": 230.0,
                        "top": 70.0,
                        "bottom": 85.0,
                    },
                ],
            }
        ]

        html_files = HTMLPageGenerator().generate_html_pages(
            pages_data=pages_data,
            output_dir=str(tmp_path),
        )
        assert len(html_files) == 1

        epub_path = tmp_path / "result.epub"
        EPUBGenerator().generate_epub(
            html_dir=str(tmp_path),
            image_dir=str(tmp_path),
            output_filename=str(epub_path),
            title="41542",
            language="ru",
        )
        assert epub_path.exists()

        with zipfile.ZipFile(epub_path, "r") as archive:
            names = archive.namelist()
            assert names[0] == "mimetype"
            assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
            assert archive.read("mimetype").decode("utf-8") == "application/epub+zip"
            assert archive.testzip() is None

            page_name = [name for name in names if name.startswith("EPUB/page_") and name.endswith(".xhtml")][0]
            page_xhtml = archive.read(page_name).decode("utf-8")
            assert "data-text" not in page_xhtml
            assert "class=\"page-figure fixed-layout-figure\"" in page_xhtml
            assert "class=\"page-image\"" in page_xhtml
            assert "class=\"text-overlay\"" in page_xhtml
            assert "class=\"overlay-word\"" in page_xhtml
            assert "Регистрационный" in page_xhtml
            assert "<section class=\"page-text\">" not in page_xhtml

            content_opf = archive.read("EPUB/content.opf").decode("utf-8")
            assert "<dc:language>ru</dc:language>" in content_opf
            assert "<meta property=\"rendition:layout\">pre-paginated</meta>" in content_opf
            assert '<item id="nav"' in content_opf
            assert '<itemref idref="nav"' not in content_opf


def test_character_overlay_copies_text_without_inserted_spaces():
    """Formatting around positioned character spans must not change copied text."""
    with tempfile.TemporaryDirectory(prefix="overlay_text_test_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        image_path = tmp_path / "page_001.png"
        Image.new("RGB", (64, 64), color="white").save(image_path)

        source_text = "Рэгістрацыйны знак"
        boxes = []
        left = 10.0
        for character in source_text:
            width = 3.0 if character == " " else 7.0
            boxes.append(
                {
                    "text": character,
                    "x0": left,
                    "x1": left + width,
                    "top": 10.0,
                    "bottom": 20.0,
                }
            )
            left += width

        output_path = tmp_path / "page_001.xhtml"
        HTMLPageGenerator().generate_page_html(
            {
                "page_number": 1,
                "image_path": str(image_path),
                "width": 200.0,
                "height": 100.0,
                "text_boxes": boxes,
            },
            str(output_path),
        )

        root = ET.fromstring(output_path.read_text(encoding="utf-8"))
        namespace = {"xhtml": "http://www.w3.org/1999/xhtml"}
        overlay = root.find(".//xhtml:div[@class='text-overlay']", namespace)

        assert overlay is not None
        assert "".join(overlay.itertext()) == source_text
