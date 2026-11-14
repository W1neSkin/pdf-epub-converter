//! Разбор PDF в структуры документа.
//!
//! Сначала исполняются команды страницы. Потом соседние глифы собираются в строки.
//! Таблица находится либо по нарисованной сетке, либо по колонкам коротких слов.

mod exec;
mod faces;
mod font;
mod group;
mod matrix;
mod table_words;
mod outline;
mod page;
mod words;

use lopdf::{decode_text_string, Document as PdfFile, Object, ObjectStream};

use crate::Document;

/// Разобрать байты PDF. Текст берётся из команд файла, не из распознавания картинки.
pub fn parse_pdf(data: &[u8]) -> Result<Document, String> {
    parse_loaded(data, None)
}

/// Одна страница, номер с единицы. Нужна, чтобы проверить скан, не разбирая всю книгу.
pub fn parse_pdf_page(data: &[u8], page: u32) -> Result<Document, String> {
    parse_loaded(data, Some(page))
}

fn parse_loaded(data: &[u8], only: Option<u32>) -> Result<Document, String> {
    let mut file = PdfFile::load_mem(data).map_err(|err| err.to_string())?;
    // В этих файлах указатель объектов внутри потока разделён нулевыми байтами.
    // Для PDF это пробел, а стандартный разбор так не считает и теряет каталог.
    recover_object_streams(&mut file);
    let mut document = if let Some(page) = only {
        page::parse_some(&file, Some(page))?
    } else {
        page::parse_file(&file)?
    };
    document.title = info_text(&file, b"Title");
    document.language = catalog_lang(&file);
    document.outline = outline::headings_from(&file);
    document.faces = faces::collect(&file);
    Ok(document)
}

fn info_text(file: &PdfFile, key: &[u8]) -> String {
    let Ok(info) = file.trailer.get(b"Info") else { return String::new() };
    let dict = if let Ok(id) = info.as_reference() {
        file.get_object(id).ok().and_then(|object| object.as_dict().ok())
    } else {
        info.as_dict().ok()
    };
    let Some(dict) = dict else { return String::new() };
    dict.get(key).ok().and_then(|object| decode_text_string(object).ok()).unwrap_or_default()
}

fn catalog_lang(file: &PdfFile) -> String {
    let Ok(catalog) = file.catalog() else { return String::new() };
    let Ok(value) = catalog.get(b"Lang") else { return String::new() };
    let bytes = value.as_str().or_else(|_| value.as_name()).unwrap_or(b"");
    let text = String::from_utf8_lossy(bytes).trim().to_string();
    if !text.is_empty() && text.chars().all(|ch| ch.is_ascii_alphanumeric() || ch == '-') {
        text
    } else {
        String::new()
    }
}

fn recover_object_streams(doc: &mut PdfFile) {
    let ids: Vec<_> = doc.objects.keys().copied().collect();
    let mut recovered = Vec::new();
    for id in ids {
        let Some(Object::Stream(stream)) = doc.objects.get_mut(&id) else { continue };
        let Ok(kind) = stream.dict.get(b"Type").and_then(Object::as_name) else { continue };
        if kind != b"ObjStm" {
            continue;
        }
        let first = stream.dict.get(b"First").and_then(Object::as_i64).unwrap_or(0).max(0) as usize;
        let end = first.min(stream.content.len());
        for byte in &mut stream.content[..end] {
            if *byte == 0 {
                *byte = b' ';
            }
        }
        if let Ok(parsed) = ObjectStream::new(stream) {
            recovered.extend(parsed.objects);
        }
    }
    for (id, object) in recovered {
        doc.objects.entry(id).or_insert(object);
    }
}
