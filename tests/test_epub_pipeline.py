import sys
import tempfile
import zipfile
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
