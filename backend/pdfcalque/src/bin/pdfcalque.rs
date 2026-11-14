//! Команды для внешнего конвертера.
//!
//! `pdfcalque export input.pdf output.epub output.json` — EPUB и отчёт.
//! `pdfcalque tables input.pdf output.json` — только отчёт, без EPUB.
//! Конвертер сравнивает отчёт со своим разбором и оставляет тот, где страницы или клетки лучше.

use std::fs;
use std::path::Path;

use pdfcalque::{write_epub, Document, Element, Image, Page};

fn main() {
    let mut args = std::env::args().skip(1);
    let command = args.next().unwrap_or_default();
    let pdf = match args.next() {
        Some(path) => path,
        None => usage(),
    };
    let bytes = match fs::read(&pdf) {
        Ok(bytes) => bytes,
        Err(err) => fail(err.to_string()),
    };
    let doc = match pdfcalque::parse_pdf(&bytes) {
        Ok(doc) => doc,
        Err(err) => fail(err),
    };
    // export пишет книгу и отчёт. tables нужен, когда EPUB не требуется.
    let json = match command.as_str() {
        "export" => {
            let epub = match args.next() {
                Some(path) => path,
                None => usage(),
            };
            if let Err(err) = write_epub(&doc, Path::new(&epub)) {
                fail(err);
            }
            match args.next() {
                Some(path) => path,
                None => usage(),
            }
        }
        "tables" => match args.next() {
            Some(path) => path,
            None => usage(),
        },
        _ => usage(),
    };
    if let Some(dir) = Path::new(&json).parent() {
        fs::create_dir_all(dir).ok();
    }
    if let Err(err) = fs::write(&json, report_json(&doc)) {
        fail(err.to_string());
    }
}

fn usage() -> ! {
    eprintln!("usage: pdfcalque export input.pdf output.epub output.json");
    eprintln!("       pdfcalque tables input.pdf output.json");
    std::process::exit(2);
}

fn fail(message: String) -> ! {
    eprintln!("{message}");
    std::process::exit(1);
}

/// Цифры, по которым конвертер решает, чей результат оставить.
fn report_json(doc: &Document) -> String {
    let mut text_chars = 0usize;
    let mut words = 0usize;
    let mut images = 0usize;
    let mut full_page_images = 0usize;
    let mut paths = 0usize;
    let mut tables = String::new();
    for (index, page) in doc.pages.iter().enumerate() {
        count_page(page, &mut text_chars, &mut words, &mut images, &mut full_page_images, &mut paths);
        for element in &page.elements {
            let Element::Table(table) = element else { continue };
            if !tables.is_empty() {
                tables.push(',');
            }
            // bbox как у pdfplumber: лево, верх, право, низ. Ноль сверху, как в их Excel.
            let left = table.bounds.x;
            let right = table.bounds.x + table.bounds.width;
            let top = page.height - (table.bounds.y + table.bounds.height);
            let bottom = page.height - table.bounds.y;
            tables.push_str(&format!(
                "{{\"page\":{},\"bbox\":[{left},{top},{right},{bottom}],\"rows\":[",
                index + 1
            ));
            for (row_index, row) in table.rows.iter().enumerate() {
                if row_index > 0 {
                    tables.push(',');
                }
                tables.push('[');
                for (cell_index, cell) in row.cells.iter().enumerate() {
                    if cell_index > 0 {
                        tables.push(',');
                    }
                    tables.push('"');
                    tables.push_str(&json_escape(&cell_string(&cell.content)));
                    tables.push('"');
                }
                tables.push(']');
            }
            tables.push_str("]}");
        }
    }
    format!(
        "{{\"pages\":{},\"text_chars\":{text_chars},\"words\":{words},\"language\":\"{}\",\"images\":{images},\"full_page_images\":{full_page_images},\"paths\":{paths},\"tables\":[{tables}]}}\n",
        doc.pages.len(),
        json_escape(&doc.language)
    )
}

fn count_page(page: &Page, text_chars: &mut usize, words: &mut usize, images: &mut usize, full_page_images: &mut usize, paths: &mut usize) {
    for element in &page.elements {
        match element {
            Element::Text(text) => add_text(text, text_chars, words),
            Element::Image(image) => {
                *images += 1;
                if covers_page(page, image) {
                    *full_page_images += 1;
                }
            }
            Element::Path(_) => *paths += 1,
            Element::Table(table) => {
                for row in &table.rows {
                    for cell in &row.cells {
                        for child in &cell.content {
                            if let Element::Text(text) = child {
                                add_text(text, text_chars, words);
                            }
                        }
                    }
                }
            }
        }
    }
}

fn covers_page(page: &Page, image: &Image) -> bool {
    image.bounds.width > page.width * 0.5 && image.bounds.height > page.height * 0.5
}

fn add_text(text: &pdfcalque::TextBlock, text_chars: &mut usize, words: &mut usize) {
    for line in &text.lines {
        for span in &line.spans {
            *text_chars += span.text.chars().count();
            *words += span.text.split_whitespace().count();
        }
    }
}

fn cell_string(elements: &[Element]) -> String {
    let mut text = String::new();
    for element in elements {
        let Element::Text(block) = element else { continue };
        for line in &block.lines {
            // Как в CSV: пробел только там, где между кусками строки есть щель.
            let mut previous: Option<(f32, f32)> = None;
            for span in &line.spans {
                if let Some((right, size)) = previous {
                    let gap = span.bounds.x - right;
                    if gap > size * 0.15 && !text.ends_with(' ') {
                        text.push(' ');
                    }
                } else if !text.is_empty() && !text.ends_with(' ') {
                    text.push(' ');
                }
                text.push_str(&span.text);
                previous = Some((span.bounds.x + span.bounds.width, span.font.size.max(1.0)));
            }
        }
    }
    text
}

fn json_escape(text: &str) -> String {
    let mut out = String::new();
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}
