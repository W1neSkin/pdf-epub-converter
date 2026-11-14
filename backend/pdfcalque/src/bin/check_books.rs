//! Прогон папки с PDF: для каждого файла страницы, элементы и ошибка разбора.
//! HTML пишется только для одной внутренней страницы, чтобы сверить её с PDF.

use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use pdfcalque::{parse_pdf, write_html, Document, Element};

fn main() {
    let root = std::env::args().nth(1).unwrap_or_else(|| r"E:\Downloads\Books".into());
    let start_at: usize = std::env::args().nth(2).and_then(|v| v.parse().ok()).unwrap_or(0);
    let preview = PathBuf::from("target/preview/books");
    let _ = fs::create_dir_all(&preview);
    let mut files = Vec::new();
    let root_path = Path::new(&root);
    if root_path.is_file() {
        files.push(root_path.to_path_buf());
    } else {
        collect(root_path, &mut files);
        files.sort();
    }
    println!("files {}", files.len());
    for (index, path) in files.iter().enumerate().skip(start_at) {
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("?");
        let started = Instant::now();
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(err) => {
                println!("READ\t{index}\t{err}\t{name}");
                continue;
            }
        };
        match parse_pdf(&bytes) {
            Ok(doc) => {
                let stats = tally(&doc);
                let ms = started.elapsed().as_millis();
                println!(
                    "OK\t{index}\tpages={}\ttext={}\timages={}\tpaths={}\ttables={}\t{ms}ms\t{name}",
                    doc.pages.len(),
                    stats.0,
                    stats.1,
                    stats.2,
                    stats.3
                );
                if doc.pages.is_empty() {
                    println!("EMPTY\t{index}\t{name}");
                    continue;
                }
                let sample = sample_page(&doc);
                let dir = preview.join(format!("{index:02}"));
                let one = Document {
                    pages: vec![doc.pages[sample].clone()],
                    title: doc.title.clone(),
                    language: doc.language.clone(),
                    outline: Vec::new(),
                    faces: Vec::new(),
                };
                if let Err(err) = write_html(&one, &dir) {
                    println!("HTML\t{index}\t{err}");
                }
                let _ = fs::write(dir.join("page.txt"), sample.to_string());
            }
            Err(err) => {
                let ms = started.elapsed().as_millis();
                let err = err.replace('\n', " ");
                println!("ERR\t{index}\t{ms}ms\t{err}\t{name}");
            }
        }
    }
}

fn collect(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect(&path, out);
        } else if path.extension().and_then(|ext| ext.to_str()) == Some("pdf") {
            out.push(path);
        }
    }
}

fn tally(doc: &Document) -> (usize, usize, usize, usize) {
    let mut counts = (0, 0, 0, 0);
    for page in &doc.pages {
        add(&page.elements, &mut counts);
    }
    counts
}

fn add(elements: &[Element], counts: &mut (usize, usize, usize, usize)) {
    for element in elements {
        match element {
            Element::Text(text) => counts.0 += text.lines.iter().map(|line| line.spans.len()).sum::<usize>(),
            Element::Image(_) => counts.1 += 1,
            Element::Path(_) => counts.2 += 1,
            Element::Table(table) => {
                counts.3 += 1;
                for row in &table.rows {
                    for cell in &row.cells {
                        add(&cell.content, counts);
                    }
                }
            }
        }
    }
}

/// Не обложка: третья страница, если она есть.
fn sample_page(doc: &Document) -> usize {
    if doc.pages.len() > 8 { 8 } else { 0 }
}
