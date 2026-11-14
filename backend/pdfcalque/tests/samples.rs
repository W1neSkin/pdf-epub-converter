//! Проверка на файлах извне.
//! f1040 — форма IRS, публичный документ США: текст и векторные линии.
//! multicolumn — две колонки текста из набора py-pdf/sample-files.
//! fax-scan — страница-картинка в сжатии факса CCITT, тоже из этого набора.
//! ShowText-ShadingPattern — маленький пример pdf.js с текстом и заливкой.

use std::path::PathBuf;

use pdfcalque::{parse_pdf, Element};

#[test]
fn write_sample_html() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target/preview");
    for name in ["f1040.pdf", "tagged.pdf", "fax-scan.pdf", "multicolumn.pdf", "pdflatex-image.pdf", "ShowText-ShadingPattern.pdf"] {
        let path = fixture(name);
        if !path.exists() {
            continue;
        }
        let bytes = std::fs::read(&path).unwrap();
        let doc = parse_pdf(&bytes).unwrap_or_else(|err| panic!("{name}: {err}"));
        let dir = root.join(name.trim_end_matches(".pdf"));
        pdfcalque::write_html(&doc, &dir).unwrap();
        std::fs::copy(&path, dir.join("original.pdf")).unwrap();
    }
}

#[test]
fn irs_form_has_text_and_lines() {
    let doc = parse_pdf(&read("f1040.pdf")).expect("f1040");
    let text = collect_text(&doc);
    assert!(text.contains("1040"), "no form number in: {}", snippet(&text));
    assert!(count(&doc, true) > 0, "form lines missing");
    assert!(doc.pages[0].width > 500.0 && doc.pages[0].height > 700.0);
}

#[test]
fn two_column_text_uses_both_sides() {
    let doc = parse_pdf(&read("multicolumn.pdf")).expect("columns");
    let xs: Vec<f32> = glyphs(&doc).iter().map(|glyph| glyph.origin.x).collect();
    assert!(xs.iter().any(|x| *x < 200.0), "no left column");
    assert!(xs.iter().any(|x| *x > 320.0), "no right column");
    let tables: Vec<_> = doc.pages.iter().enumerate().flat_map(|(index, page)| {
        page.elements.iter().filter_map(move |element| match element {
            Element::Table(table) => Some((index, table)),
            _ => None,
        })
    }).collect();
    // Первые страницы — две колонки статьи. Таблица стран на последней странице — настоящая.
    assert!(tables.iter().all(|(index, _)| *index + 1 == doc.pages.len()), "book columns became a table: {tables:?}");
    let table = tables[0].1;
    let csv = pdfcalque::table_to_csv(table);
    assert!(csv.contains("Austria") && csv.contains("Vienna"), "{csv}");
    assert!(csv.contains("German"), "{csv}");
    assert!(!csv.contains("Germ a"), "{csv}");
}

#[test]
fn tagged_pdf_keeps_form_text_and_image() {
    let doc = parse_pdf(&read("tagged.pdf")).expect("tagged");
    let text = collect_text(&doc);
    assert!(text.contains("Structure destinations"), "{}", snippet(&text));
    assert!(text.contains("form XObject"), "form text missing: {}", snippet(&text));
    let image = doc.pages.iter().flat_map(|page| &page.elements).find_map(|element| match element {
        Element::Image(image) => Some(image),
        _ => None,
    }).expect("image");
    assert!((image.bounds.x - 72.0).abs() < 1.0, "image x {}", image.bounds.x);
    assert!((image.bounds.y - 620.0).abs() < 1.0, "image y {}", image.bounds.y);
    assert!((image.bounds.width - 200.0).abs() < 1.0);
    assert!((image.bounds.height - 100.0).abs() < 1.0);
    let form = glyphs(&doc).into_iter().find(|glyph| glyph.ch == Some('T') && (glyph.origin.y - 700.0).abs() < 2.0);
    let form = form.expect("form text baseline");
    assert!((form.origin.x - 72.0).abs() < 1.0, "form x {}", form.origin.x);
}

#[test]
fn fax_scan_is_an_image() {
    let doc = parse_pdf(&read("fax-scan.pdf")).expect("fax");
    let page = &doc.pages[0];
    let covers = page.elements.iter().any(|element| match element {
        Element::Image(image) => image.bounds.width > page.width * 0.5 && image.bounds.height > page.height * 0.5,
        _ => false,
    });
    assert!(covers, "fax page has no full-page image");
    let html = pdfcalque::page_to_html(page);
    assert!(html.contains("data:image/png"), "fax pixels were not decoded");
}

#[test]
fn stolyarov_preface_is_russian() {
    let path = PathBuf::from(r"E:\Downloads\Books\2026.03\Столяров А.В. - Программирование - введение в профессию (Издание 2,91) - 2025\Столяров А.В. - Программирование - введение в профессию. Том 1 - Азы программирования.pdf");
    if !path.exists() {
        return;
    }
    let doc = parse_pdf(&std::fs::read(&path).unwrap()).expect("stolyarov");
    let text = collect_text(&doc);
    let high: String = text.chars().filter(|ch| (*ch as u32) > 127).take(40).collect();
    assert!(text.contains("Предисловие"), "russian letters missing: {} | high: {high}", snippet(&text));
}

#[test]
fn latex_page_has_an_image_and_words() {
    let doc = parse_pdf(&read("pdflatex-image.pdf")).expect("image pdf");
    assert!(count_images(&doc) > 0);
    assert!(collect_text(&doc).chars().any(|ch| ch.is_alphanumeric()));
}

#[test]
fn shading_sample_keeps_its_word() {
    let path = fixture("ShowText-ShadingPattern.pdf");
    if !path.exists() {
        return;
    }
    let doc = parse_pdf(&std::fs::read(&path).unwrap()).expect("shading sample");
    assert!(collect_text(&doc).chars().any(|ch| ch.is_alphanumeric()));
}

fn read(name: &str) -> Vec<u8> {
    std::fs::read(fixture(name)).unwrap_or_else(|err| panic!("fixture {name}: {err}"))
}

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests").join("fixtures").join(name)
}

fn count(doc: &pdfcalque::Document, paths: bool) -> usize {
    doc.pages.iter().map(|page| count_elements(&page.elements, paths)).sum()
}

fn count_elements(elements: &[Element], paths: bool) -> usize {
    elements.iter().map(|element| match element {
        Element::Path(_) if paths => 1,
        Element::Table(table) => table.rows.iter().map(|row| row.cells.iter().map(|cell| count_elements(&cell.content, paths)).sum::<usize>()).sum(),
        _ => 0,
    }).sum()
}

fn count_images(doc: &pdfcalque::Document) -> usize {
    doc.pages.iter().flat_map(|page| &page.elements).filter(|element| matches!(element, Element::Image(_))).count()
}

fn glyphs(doc: &pdfcalque::Document) -> Vec<&pdfcalque::Glyph> {
    let mut out = Vec::new();
    for page in &doc.pages {
        for element in &page.elements {
            push_glyphs(element, &mut out);
        }
    }
    out
}

fn push_glyphs<'a>(element: &'a Element, out: &mut Vec<&'a pdfcalque::Glyph>) {
    match element {
        Element::Text(text) => {
            for line in &text.lines {
                for span in &line.spans {
                    out.extend(&span.glyphs);
                }
            }
        }
        Element::Table(table) => {
            for row in &table.rows {
                for cell in &row.cells {
                    for child in &cell.content {
                        push_glyphs(child, out);
                    }
                }
            }
        }
        _ => {}
    }
}

fn collect_text(doc: &pdfcalque::Document) -> String {
    let mut out = String::new();
    for page in &doc.pages {
        for element in &page.elements {
            push_text(element, &mut out);
        }
    }
    out
}

fn push_text(element: &Element, out: &mut String) {
    match element {
        Element::Text(text) => {
            for line in &text.lines {
                for span in &line.spans {
                    out.push_str(&span.text);
                    out.push(' ');
                }
            }
        }
        Element::Table(table) => {
            for row in &table.rows {
                for cell in &row.cells {
                    for child in &cell.content {
                        push_text(child, out);
                    }
                }
            }
        }
        _ => {}
    }
}

fn snippet(text: &str) -> String {
    text.chars().take(180).collect()
}
