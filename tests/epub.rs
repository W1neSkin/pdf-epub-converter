use std::io::{Cursor, Read};

use pdfcalque::{document_to_epub, parse_pdf, write_epub, Document, Face, Heading, Page};
use zip::ZipArchive;

#[test]
fn epub_has_toc_tree_and_page_links() {
    let doc = Document {
        pages: vec![
            Page { width: 100.0, height: 200.0, elements: vec![] },
            Page { width: 100.0, height: 200.0, elements: vec![] },
        ],
        title: "Проба".into(),
        language: "ru".into(),
        outline: vec![Heading {
            title: "Глава".into(),
            page: 0,
            y: Some(10.0),
            children: vec![Heading { title: "Раздел".into(), page: 1, y: Some(80.0), children: vec![] }],
        }],
        faces: vec![Face { family: "Demo".into(), bold: false, italic: false, data: b"OTTOdemo".to_vec() }],
    };
    let bytes = document_to_epub(&doc).unwrap();
    let mut archive = ZipArchive::new(Cursor::new(bytes)).unwrap();
    {
        let first = archive.by_index(0).unwrap();
        assert_eq!(first.name().unwrap(), "mimetype");
        assert_eq!(first.compression(), zip::CompressionMethod::Stored);
    }

    let nav = read(&mut archive, "OEBPS/nav.xhtml");
    assert!(nav.contains("Оглавление"));
    assert!(nav.contains("Глава"));
    assert!(nav.contains("<ol><li><a href=\"page-002.xhtml#h2\">Раздел</a></li></ol>"), "{nav}");
    assert!(nav.contains("epub:type=\"page-list\""));

    let opf = read(&mut archive, "OEBPS/content.opf");
    assert!(opf.contains("pre-paginated"));
    assert!(opf.contains("page-001.xhtml"));
    assert!(opf.contains("page-002.xhtml"));

    let page = read(&mut archive, "OEBPS/page-001.xhtml");
    assert!(page.contains("rel=\"next\" href=\"page-002.xhtml\""));
    assert!(page.contains("id=\"h1\""));
    let last = read(&mut archive, "OEBPS/page-002.xhtml");
    assert!(last.contains("id=\"h2\""));
    assert!(last.contains("rel=\"prev\" href=\"page-001.xhtml\""));
    let ncx = read(&mut archive, "OEBPS/toc.ncx");
    assert!(ncx.contains("dtb:depth\" content=\"2\""));
    assert!(ncx.contains("navPoint"));
    assert!(ncx.contains("Раздел"));
    let css = read(&mut archive, "OEBPS/styles.css");
    assert!(css.contains("@font-face"), "{css}");
    assert!(css.contains("fonts/Demo.otf"), "{css}");
    let font = archive.by_name("OEBPS/fonts/Demo.otf").unwrap();
    assert_eq!(font.size(), 8);
}

#[test]
fn stolyarov_outline_is_a_book_tree() {
    let path = std::path::PathBuf::from(r"E:\Downloads\Books\2026.03\Столяров А.В. - Программирование - введение в профессию (Издание 2,91) - 2025\Столяров А.В. - Программирование - введение в профессию. Том 1 - Азы программирования.pdf");
    if !path.exists() {
        return;
    }
    let doc = parse_pdf(&std::fs::read(&path).unwrap()).expect("stolyarov");
    assert!(!doc.outline.is_empty(), "pdf has no bookmarks");
    assert!(doc.outline.iter().any(|item| !item.children.is_empty()), "bookmarks are a flat list");
    let pair = same_page_spots(&doc.outline).expect("two bookmarks on one page should land in different places");
    let out = std::path::Path::new("target/preview/stolyarov.epub");
    write_epub(&doc, out).unwrap();
    let mut archive = ZipArchive::new(std::fs::File::open(out).unwrap()).unwrap();
    let nav = read(&mut archive, "OEBPS/nav.xhtml");
    assert!(nav.contains(&format!("page-{:03}.xhtml#{}", pair.0.page + 1, pair.0.id)));
    assert!(nav.contains(&format!("page-{:03}.xhtml#{}", pair.1.page + 1, pair.1.id)));
    assert_ne!(pair.0.id, pair.1.id);
    let page = read(&mut archive, &format!("OEBPS/page-{:03}.xhtml", pair.0.page + 1));
    assert!(page.contains(&format!("id=\"{}\"", pair.0.id)));
    assert!(page.contains(&format!("id=\"{}\"", pair.1.id)));
    assert!(page.contains("textLength="), "letters are not fitted to the PDF widths");
    assert!(page.contains("Times New Roman"), "book font fell back to sans-serif");
}

struct SpotRef {
    page: usize,
    id: String,
}

fn same_page_spots(items: &[Heading]) -> Option<(SpotRef, SpotRef)> {
    let mut flat = Vec::new();
    flatten(items, &mut flat);
    for left in 0..flat.len() {
        for right in left + 1..flat.len() {
            let (a_page, a_y, a_id) = &flat[left];
            let (b_page, b_y, b_id) = &flat[right];
            if a_page == b_page && (a_y - b_y).abs() > 40.0 {
                return Some((
                    SpotRef { page: *a_page, id: a_id.clone() },
                    SpotRef { page: *b_page, id: b_id.clone() },
                ));
            }
        }
    }
    None
}

fn flatten(items: &[Heading], out: &mut Vec<(usize, f32, String)>) {
    for item in items {
        let id = format!("h{}", out.len() + 1);
        out.push((item.page, item.y.unwrap_or(0.0), id));
        flatten(&item.children, out);
    }
}

fn read<R: std::io::Read + std::io::Seek>(archive: &mut ZipArchive<R>, name: &str) -> String {
    let mut file = archive.by_name(name).unwrap();
    let mut text = String::new();
    file.read_to_string(&mut text).unwrap();
    text
}
