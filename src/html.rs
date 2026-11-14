//! Запись разобранной страницы в HTML.
//!
//! Внутри страницы один SVG. Координаты PDF идут снизу вверх, у SVG сверху вниз,
//! поэтому высота страницы минус y переносит точку на то же место листа.

use std::fs;
use std::path::Path;

use flate2::write::ZlibEncoder;
use flate2::Compression;
use std::io::Write;

use crate::{Color, Document, Element, Font, Image, Page, PathSegment, PathShape, TextBlock};

/// Все страницы одним HTML-файлом. Каждая страница — свой SVG исходного размера.
/// Для печати у листа есть разрыв страницы. EPUB потом сможет взять те же страницы по отдельности.
pub fn document_to_html(doc: &Document) -> String {
    let mut pages = String::new();
    for page in &doc.pages {
        let mut body = String::new();
        write_elements(&mut body, &page.elements, page.height);
        pages.push_str(&format!(
            "<section class=\"page\"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}pt\" height=\"{h}pt\" viewBox=\"0 0 {w} {h}\">{body}</svg></section>\n",
            w = num(page.width),
            h = num(page.height),
        ));
    }
    format!(
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>document</title>\n<style>body{{margin:0;background:#ddd}} .page{{background:#fff;margin:16px auto;width:fit-content}} svg{{display:block}} @media print{{body{{background:#fff}} .page{{margin:0;break-after:page}}}}</style></head>\n<body>\n{pages}</body></html>\n"
    )
}

pub fn write_document(doc: &Document, path: &Path) -> Result<(), String> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir).map_err(|err| err.to_string())?;
    }
    fs::write(path, document_to_html(doc)).map_err(|err| err.to_string())
}

/// Один HTML-файл на страницу: `page-1.html`, `page-2.html`, ...
pub fn write_html(doc: &Document, dir: &Path) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|err| err.to_string())?;
    for (index, page) in doc.pages.iter().enumerate() {
        let path = dir.join(format!("page-{}.html", index + 1));
        fs::write(&path, page_to_html(page)).map_err(|err| err.to_string())?;
    }
    Ok(())
}

pub(crate) fn page_svg(page: &Page) -> String {
    let mut body = String::new();
    write_elements(&mut body, &page.elements, page.height);
    format!(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}pt\" height=\"{h}pt\" viewBox=\"0 0 {w} {h}\">{body}</svg>",
        w = num(page.width),
        h = num(page.height),
    )
}

pub fn page_to_html(page: &Page) -> String {
    let body = page_svg(page);
    format!(
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>page</title>\n<style>html,body{{margin:0;background:#ddd}}svg{{background:#fff;display:block}}</style></head>\n<body>{body}</body></html>\n"
    )
}

fn write_elements(out: &mut String, elements: &[Element], page_h: f32) {
    for element in elements {
        match element {
            Element::Text(text) => write_text(out, text, page_h),
            Element::Image(image) => write_image(out, image, page_h),
            Element::Path(path) => write_path(out, path, page_h),
            Element::Table(table) => {
                for row in &table.rows {
                    for cell in &row.cells {
                        // Рамку рисуем только если она была в PDF. Иначе на странице
                        // появляются линии, которых в книге нет.
                        if table.ruled {
                            let top = page_h - (cell.bounds.y + cell.bounds.height);
                            out.push_str(&format!(
                                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" fill=\"none\" stroke=\"#000\" stroke-width=\"0.6\"/>",
                                num(cell.bounds.x), num(top), num(cell.bounds.width), num(cell.bounds.height)
                            ));
                        }
                        write_elements(out, &cell.content, page_h);
                    }
                }
            }
        }
    }
}

fn write_text(out: &mut String, text: &TextBlock, page_h: f32) {
    if !text.visible {
        return;
    }
    for line in &text.lines {
        for span in &line.spans {
            let family = font_family(&span.font);
            let weight = if span.font.bold { "700" } else { "400" };
            let style = if span.font.italic { "italic" } else { "normal" };
            for glyph in &span.glyphs {
                let Some(ch) = glyph.ch else { continue };
                let y = page_h - glyph.origin.y;
                let turn = if glyph.rotation.abs() > 0.5 {
                    format!(" transform=\"rotate({} {} {})\"", num(glyph.rotation), num(glyph.origin.x), num(y))
                } else {
                    String::new()
                };
                // Ширина буквы в PDF уже известна. Без неё системный шрифт шире
                // и заползает на соседнюю букву, пробел между словами пропадает.
                let fit = if glyph.rotation.abs() < 0.5 && glyph.bounds.width > 0.2 {
                    format!(" textLength=\"{}\" lengthAdjust=\"spacingAndGlyphs\"", num(glyph.bounds.width))
                } else {
                    String::new()
                };
                let fill = if span.color.a < 0.01 { "transparent" } else { &css_color(span.color) };
                out.push_str(&format!(
                    "<text x=\"{}\" y=\"{}\" font-size=\"{}\" font-family=\"{}\" font-weight=\"{weight}\" font-style=\"{style}\" fill=\"{fill}\"{fit}{turn}>{}</text>",
                    num(glyph.origin.x), num(y), num(span.font.size), family, escape(&ch.to_string())
                ));
            }
        }
    }
}

fn write_path(out: &mut String, path: &PathShape, page_h: f32) {
    let mut d = String::new();
    for segment in &path.segments {
        match segment {
            PathSegment::Move(p) => d.push_str(&format!("M{} {} ", num(p.x), num(page_h - p.y))),
            PathSegment::Line(p) => d.push_str(&format!("L{} {} ", num(p.x), num(page_h - p.y))),
            PathSegment::Curve { c1, c2, end } => d.push_str(&format!(
                "C{} {} {} {} {} {} ",
                num(c1.x), num(page_h - c1.y), num(c2.x), num(page_h - c2.y), num(end.x), num(page_h - end.y)
            )),
            PathSegment::Close => d.push_str("Z "),
        }
    }
    let fill = path.fill.map(css_color).unwrap_or_else(|| "none".into());
    let stroke = path.stroke.map(css_color).unwrap_or_else(|| "none".into());
    let rule = if path.even_odd { "evenodd" } else { "nonzero" };
    out.push_str(&format!(
        "<path d=\"{d}\" fill=\"{fill}\" stroke=\"{stroke}\" stroke-width=\"{}\" fill-rule=\"{rule}\"/>",
        num(path.stroke_width.max(0.3))
    ));
}

fn write_image(out: &mut String, image: &Image, page_h: f32) {
    let top = page_h - (image.bounds.y + image.bounds.height);
    let href = image_href(image);
    if let Some(href) = href {
        out.push_str(&format!(
            "<image x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" href=\"{href}\"/>",
            num(image.bounds.x), num(top), num(image.bounds.width), num(image.bounds.height)
        ));
    } else {
        out.push_str(&format!(
            "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" fill=\"#ddd\" stroke=\"#888\"/>",
            num(image.bounds.x), num(top), num(image.bounds.width), num(image.bounds.height)
        ));
    }
}

fn image_href(image: &Image) -> Option<String> {
    if image.filter.contains("DCTDecode") {
        return Some(format!("data:image/jpeg;base64,{}", b64(&image.data)));
    }
    let pixels = if image.filter.contains("FlateDecode") { inflate(&image.data)? } else { image.data.clone() };
    let png = raw_png(image.pixel_width, image.pixel_height, &image.color_space, &pixels)?;
    Some(format!("data:image/png;base64,{}", b64(&png)))
}

pub(crate) fn raw_png(width: u32, height: u32, space: &str, data: &[u8]) -> Option<Vec<u8>> {
    let channels: usize = if space.contains("RGB") { 3 } else { 1 };
    let need = width as usize * height as usize * channels;
    if width == 0 || height == 0 || data.len() < need {
        return None;
    }
    let color_type: u8 = if channels == 3 { 2 } else { 0 };
    let mut raw = Vec::with_capacity(need + height as usize);
    for row in 0..height as usize {
        raw.push(0);
        let start = row * width as usize * channels;
        raw.extend_from_slice(&data[start..start + width as usize * channels]);
    }
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::fast());
    encoder.write_all(&raw).ok()?;
    let compressed = encoder.finish().ok()?;
    let mut png = Vec::new();
    png.extend_from_slice(b"\x89PNG\r\n\x1a\n");
    chunk(&mut png, b"IHDR", &ihdr(width, height, color_type));
    chunk(&mut png, b"IDAT", &compressed);
    chunk(&mut png, b"IEND", &[]);
    Some(png)
}

fn ihdr(width: u32, height: u32, color_type: u8) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&width.to_be_bytes());
    bytes.extend_from_slice(&height.to_be_bytes());
    bytes.extend_from_slice(&[8, color_type, 0, 0, 0]);
    bytes
}

fn chunk(out: &mut Vec<u8>, kind: &[u8; 4], data: &[u8]) {
    out.extend_from_slice(&(data.len() as u32).to_be_bytes());
    out.extend_from_slice(kind);
    out.extend_from_slice(data);
    let mut crc_data = kind.to_vec();
    crc_data.extend_from_slice(data);
    out.extend_from_slice(&crc32(&crc_data).to_be_bytes());
}

fn crc32(data: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFFu32;
    for byte in data {
        crc ^= *byte as u32;
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
        }
    }
    !crc
}

fn inflate(data: &[u8]) -> Option<Vec<u8>> {
    let mut decoder = flate2::read::ZlibDecoder::new(data);
    let mut out = Vec::new();
    std::io::Read::read_to_end(&mut decoder, &mut out).ok()?;
    Some(out)
}

fn font_family(font: &Font) -> String {
    // Первое имя — шрифт из PDF. Его файл лежит в EPUB и подключается через @font-face.
    // Дальше запасной шрифт системы, если файла нет.
    let Some(name) = font.name.as_deref() else { return "sans-serif".into() };
    let fallback = if name.contains("Courier") || name.contains("SFTT") || name.contains("CMTT") {
        "Courier New, Courier, monospace"
    } else if name.contains("Helvetica") || name.contains("Arial") || name.contains("SFSS") {
        "Helvetica, Arial, sans-serif"
    } else {
        "Times New Roman, Times, serif"
    };
    format!("'{}', {fallback}", escape(name))
}

fn css_color(color: Color) -> String {
    format!("#{:02x}{:02x}{:02x}", byte(color.r), byte(color.g), byte(color.b))
}

fn byte(channel: f32) -> u8 {
    (channel.clamp(0.0, 1.0) * 255.0).round() as u8
}

fn escape(text: &str) -> String {
    let mut out = String::new();
    for ch in text.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            // Управляющий символ из PDF ломает XHTML: браузер обрывает страницу.
            ch if xml_char(ch) => out.push(ch),
            _ => {}
        }
    }
    out
}

fn xml_char(ch: char) -> bool {
    matches!(ch, '\t' | '\n' | '\r' | '\u{20}'..='\u{D7FF}' | '\u{E000}'..='\u{FFFD}')
}

fn num(value: f32) -> String {
    format!("{value:.2}")
}

fn b64(data: &[u8]) -> String {
    const TABLE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = chunk.get(1).copied().unwrap_or(0) as u32;
        let b2 = chunk.get(2).copied().unwrap_or(0) as u32;
        let n = (b0 << 16) | (b1 << 8) | b2;
        out.push(TABLE[(n >> 18) as usize] as char);
        out.push(TABLE[((n >> 12) & 63) as usize] as char);
        out.push(if chunk.len() > 1 { TABLE[((n >> 6) & 63) as usize] as char } else { '=' });
        out.push(if chunk.len() > 2 { TABLE[(n & 63) as usize] as char } else { '=' });
    }
    out
}
