import json
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"
SITE = "https://w1neskin.github.io/pdf-epub-converter/"


def test_sitemap_pages_have_unique_metadata_and_canonicals():
    """Every submitted URL must be a real, indexable page with useful metadata."""
    sitemap = ElementTree.parse(PUBLIC / "sitemap.xml")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [
        node.text
        for node in sitemap.findall("s:url/s:loc", namespace)
    ]
    assert len(urls) == len(set(urls)) == 4

    titles = set()
    for url in urls:
        relative_path = url.removeprefix(SITE)
        page_path = PUBLIC / (relative_path or "index.html")
        assert page_path.exists()

        soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")
        title = soup.title.get_text(strip=True)
        description = soup.find("meta", attrs={"name": "description"})
        canonical = soup.find("link", attrs={"rel": "canonical"})
        assert title and title not in titles
        assert description and description.get("content")
        assert canonical and canonical.get("href") == url
        assert soup.find("h1")
        titles.add(title)


def test_homepage_structured_data_and_llms_file_are_current():
    """Search and AI metadata must describe real project outputs."""
    soup = BeautifulSoup(
        (PUBLIC / "index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    structured_data = json.loads(
        soup.find("script", attrs={"type": "application/ld+json"}).string
    )
    graph = structured_data["@graph"]
    types = {item["@type"] for item in graph}
    assert {"WebSite", "WebApplication", "FAQPage"} <= types

    application = next(item for item in graph if item["@type"] == "WebApplication")
    features = " ".join(application["featureList"])
    assert "XLSX" in features
    assert "CSV" in features
    assert "https://github.com/W1neSkin/pdf-epub-converter" in application["sameAs"]

    llms_text = (PUBLIC / "llms.txt").read_text(encoding="utf-8")
    assert llms_text.startswith("# PDF to EPUB Converter\n\n>")
    assert f"[Features]({SITE}features.html)" in llms_text


def test_user_facing_text_uses_regular_hyphens():
    """Keep interface punctuation consistent with the project's writing style."""
    source_files = list((ROOT / "frontend" / "src").rglob("*.js"))
    public_files = list(PUBLIC.glob("*.html"))
    for path in source_files + public_files:
        assert "\N{EM DASH}" not in path.read_text(encoding="utf-8"), path
