//! Одна страница PDF в HTML, чтобы глазами сверить скан и собранный лист.

fn main() {
    let mut args = std::env::args().skip(1);
    let path = args.next().expect("pdf");
    let page: u32 = args.next().unwrap_or_else(|| "1".into()).parse().expect("page");
    let bytes = std::fs::read(&path).expect("read");
    let doc = pdfcalque::parse_pdf_page(&bytes, page).expect("parse");
    let page_data = doc.pages.first().expect("page");
    let html = pdfcalque::page_to_html(page_data);
    let out = std::path::Path::new("target/preview/scan.html");
    if let Some(dir) = out.parent() {
        std::fs::create_dir_all(dir).ok();
    }
    std::fs::write(out, html).expect("write");
    let texts = page_data.elements.iter().filter(|el| matches!(el, pdfcalque::Element::Text(_))).count();
    let images = page_data.elements.iter().filter(|el| matches!(el, pdfcalque::Element::Image(_))).count();
    let paths = page_data.elements.iter().filter(|el| matches!(el, pdfcalque::Element::Path(_))).count();
    println!("page {page} text {texts} images {images} paths {paths} -> {}", out.display());
}
