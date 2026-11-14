//! Фиксированный EPUB 3: каждая страница PDF — отдельный XHTML с тем же SVG.
//!
//! Архив ZIP. Первым и без сжатия лежит `mimetype`.
//! `META-INF/container.xml` указывает на `OEBPS/content.opf`.
//! `content.opf` перечисляет файлы и порядок чтения (spine).
//! `nav.xhtml` — оглавление EPUB 3, вложенные разделы остаются деревом.
//! `toc.ncx` — то же оглавление для старых читалок.
//! У каждой страницы есть ссылки на предыдущую и следующую.

use std::io::{Cursor, Write};
use std::time::{SystemTime, UNIX_EPOCH};

use zip::write::SimpleFileOptions;
use zip::{CompressionMethod, ZipWriter};

use crate::html::page_svg;
use crate::{Document, Face, Heading};

/// Собрать EPUB. Если в PDF не было закладок, оглавление — номера страниц.
pub fn document_to_epub(doc: &Document) -> Result<Vec<u8>, String> {
    let title = if doc.title.is_empty() { "Книга" } else { doc.title.as_str() };
    let language = if doc.language.is_empty() { "ru" } else { doc.language.as_str() };
    let id = format!("urn:pdfcalque:{}:{}", doc.pages.len(), simple_hash(title));
    let mut cursor = Cursor::new(Vec::new());
    let mut zip = ZipWriter::new(&mut cursor);
    let stored = SimpleFileOptions::default().compression_method(CompressionMethod::Stored);
    let deflated = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);

    zip.start_file("mimetype", stored).map_err(|err| err.to_string())?;
    zip.write_all(b"application/epub+zip").map_err(|err| err.to_string())?;

    write(&mut zip, deflated, "META-INF/container.xml", CONTAINER)?;
    write(&mut zip, deflated, "OEBPS/content.opf", &package(doc, title, language, &id))?;
    if !doc.faces.is_empty() {
        write(&mut zip, deflated, "OEBPS/styles.css", &stylesheet(&doc.faces))?;
        for face in &doc.faces {
            let path = format!("OEBPS/fonts/{}", font_file_name(face));
            write_bytes(&mut zip, deflated, &path, &face.data)?;
        }
    }
    let toc = if doc.outline.is_empty() { page_headings(doc) } else { doc.outline.clone() };
    let spots = spots_of(&toc);
    write(&mut zip, deflated, "OEBPS/nav.xhtml", &nav_xhtml(doc, title, &toc, &spots))?;
    write(&mut zip, deflated, "OEBPS/toc.ncx", &toc_ncx(doc, title, &id, &toc, &spots))?;
    for (index, page) in doc.pages.iter().enumerate() {
        let name = format!("OEBPS/{}", page_file(index));
        write(&mut zip, deflated, &name, &page_xhtml(page, index, doc.pages.len(), language, &spots, !doc.faces.is_empty()))?;
    }
    zip.finish().map_err(|err| err.to_string())?;
    Ok(cursor.into_inner())
}

/// Записать EPUB в файл. Расширение обычно `.epub`, внутри это тот же ZIP.
pub fn write_epub(doc: &Document, path: &std::path::Path) -> Result<(), String> {
    if let Some(dir) = path.parent() {
        if !dir.as_os_str().is_empty() {
            std::fs::create_dir_all(dir).map_err(|err| err.to_string())?;
        }
    }
    std::fs::write(path, document_to_epub(doc)?).map_err(|err| err.to_string())
}

fn write(zip: &mut ZipWriter<&mut Cursor<Vec<u8>>>, opts: SimpleFileOptions, name: &str, body: &str) -> Result<(), String> {
    write_bytes(zip, opts, name, body.as_bytes())
}

fn write_bytes(zip: &mut ZipWriter<&mut Cursor<Vec<u8>>>, opts: SimpleFileOptions, name: &str, body: &[u8]) -> Result<(), String> {
    zip.start_file(name, opts).map_err(|err| err.to_string())?;
    zip.write_all(body).map_err(|err| err.to_string())
}

fn package(doc: &Document, title: &str, language: &str, id: &str) -> String {
    let mut manifest = String::new();
    let mut spine = String::new();
    manifest.push_str("<item id=\"nav\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>");
    manifest.push_str("<item id=\"ncx\" href=\"toc.ncx\" media-type=\"application/x-dtbncx+xml\"/>");
    if !doc.faces.is_empty() {
        manifest.push_str("<item id=\"css\" href=\"styles.css\" media-type=\"text/css\"/>");
        for (index, face) in doc.faces.iter().enumerate() {
            let kind = if face.data.starts_with(&[0, 1, 0, 0]) { "font/ttf" } else { "font/otf" };
            manifest.push_str(&format!(
                "<item id=\"f{index}\" href=\"fonts/{}\" media-type=\"{kind}\"/>",
                font_file_name(face)
            ));
        }
    }
    for index in 0..doc.pages.len() {
        let idref = format!("p{}", index + 1);
        manifest.push_str(&format!(
            "<item id=\"{idref}\" href=\"{}\" media-type=\"application/xhtml+xml\" properties=\"svg\"/>",
            page_file(index)
        ));
        spine.push_str(&format!("<itemref idref=\"{idref}\"/>"));
    }
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<package xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"bookid\" version=\"3.0\" xml:lang=\"{language}\"><metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><dc:identifier id=\"bookid\">{id}</dc:identifier><dc:title>{}</dc:title><dc:language>{language}</dc:language><meta property=\"dcterms:modified\">{}</meta><meta property=\"rendition:layout\">pre-paginated</meta></metadata><manifest>{manifest}</manifest><spine toc=\"ncx\" page-progression-direction=\"ltr\">{spine}</spine></package>\n",
        xml(title),
        modified_now(),
    )
}

fn nav_xhtml(doc: &Document, title: &str, toc: &[Heading], spots: &[Spot]) -> String {
    let mut list = String::new();
    let mut cursor = 0;
    nav_list(&mut list, toc, doc.pages.len(), spots, &mut cursor);
    let mut pages = String::new();
    for index in 0..doc.pages.len() {
        pages.push_str(&format!("<li><a href=\"{}\">{}</a></li>", page_file(index), index + 1));
    }
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\"><head><title>{}</title></head><body><nav epub:type=\"toc\"><h1>Оглавление</h1><ol>{list}</ol></nav><nav epub:type=\"page-list\" hidden=\"hidden\"><ol>{pages}</ol></nav></body></html>\n",
        xml(title)
    )
}

fn nav_list(out: &mut String, items: &[Heading], count: usize, spots: &[Spot], cursor: &mut usize) {
    for item in items {
        let href = spot_href(item.page, count, spots, cursor);
        out.push_str(&format!("<li><a href=\"{href}\">{}</a>", xml(&item.title)));
        if !item.children.is_empty() {
            out.push_str("<ol>");
            nav_list(out, &item.children, count, spots, cursor);
            out.push_str("</ol>");
        }
        out.push_str("</li>");
    }
}

fn toc_ncx(doc: &Document, title: &str, id: &str, toc: &[Heading], spots: &[Spot]) -> String {
    let mut points = String::new();
    let mut cursor = 0usize;
    ncx_points(&mut points, toc, doc.pages.len(), spots, &mut cursor);
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<ncx xmlns=\"http://www.daisy.org/z3986/2005/ncx/\" version=\"2005-1\"><head><meta name=\"dtb:uid\" content=\"{id}\"/><meta name=\"dtb:depth\" content=\"{}\"/><meta name=\"dtb:totalPageCount\" content=\"{}\"/></head><docTitle><text>{}</text></docTitle><navMap>{points}</navMap></ncx>\n",
        heading_depth(&toc),
        doc.pages.len(),
        xml(title)
    )
}

fn ncx_points(out: &mut String, items: &[Heading], count: usize, spots: &[Spot], cursor: &mut usize) {
    for item in items {
        let id = *cursor + 1;
        let href = spot_href(item.page, count, spots, cursor);
        out.push_str(&format!(
            "<navPoint id=\"n{id}\" playOrder=\"{id}\"><navLabel><text>{}</text></navLabel><content src=\"{href}\"/>",
            xml(&item.title)
        ));
        ncx_points(out, &item.children, count, spots, cursor);
        out.push_str("</navPoint>");
    }
}

fn page_xhtml(page: &crate::Page, index: usize, count: usize, language: &str, spots: &[Spot], styled: bool) -> String {
    let css = if styled { "<link rel=\"stylesheet\" href=\"styles.css\"/>" } else { "" };
    let prev = if index > 0 {
        format!("<link rel=\"prev\" href=\"{}\"/>", page_file(index - 1))
    } else {
        String::new()
    };
    let next = if index + 1 < count {
        format!("<link rel=\"next\" href=\"{}\"/>", page_file(index + 1))
    } else {
        String::new()
    };
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"{language}\"><head><title>Страница {}</title><meta name=\"viewport\" content=\"width={}, height={}\"/>{prev}{next}{css}<style>html,body{{margin:0;background:#fff}} svg{{display:block;width:100%;height:auto}}</style></head><body>{}</body></html>\n",
        index + 1,
        num(page.width),
        num(page.height),
        with_anchors(page_svg(page), &anchor_marks(spots, index))
    )
}

struct Spot {
    page: usize,
    y: f32,
    id: String,
}

fn spots_of(items: &[Heading]) -> Vec<Spot> {
    let mut spots = Vec::new();
    collect_spots(items, &mut spots);
    spots
}

fn collect_spots(items: &[Heading], spots: &mut Vec<Spot>) {
    for item in items {
        let id = format!("h{}", spots.len() + 1);
        spots.push(Spot { page: item.page, y: item.y.unwrap_or(0.0), id });
        collect_spots(&item.children, spots);
    }
}

fn spot_href(page: usize, count: usize, spots: &[Spot], cursor: &mut usize) -> String {
    let id = spots.get(*cursor).map(|spot| spot.id.as_str()).unwrap_or("h0");
    *cursor += 1;
    format!("{}#{id}", page_href(page, count))
}

fn anchor_marks(spots: &[Spot], page: usize) -> String {
    let mut out = String::new();
    for spot in spots.iter().filter(|spot| spot.page == page) {
        out.push_str(&format!(
            "<rect id=\"{}\" x=\"0\" y=\"{}\" width=\"2\" height=\"2\" fill=\"none\"/>",
            spot.id,
            num(spot.y)
        ));
    }
    out
}

fn with_anchors(svg: String, anchors: &str) -> String {
    let Some(end) = svg.find('>') else { return svg };
    let mut out = String::with_capacity(svg.len() + anchors.len());
    out.push_str(&svg[..=end]);
    out.push_str(anchors);
    out.push_str(&svg[end + 1..]);
    out
}

fn heading_depth(items: &[Heading]) -> usize {
    items.iter().map(|item| 1 + heading_depth(&item.children)).max().unwrap_or(0)
}

fn page_headings(doc: &Document) -> Vec<Heading> {
    (0..doc.pages.len())
        .map(|page| Heading { title: format!("Страница {}", page + 1), page, y: None, children: Vec::new() })
        .collect()
}

fn stylesheet(faces: &[Face]) -> String {
    let mut css = String::new();
    for face in faces {
        let weight = if face.bold { 700 } else { 400 };
        let style = if face.italic { "italic" } else { "normal" };
        let format = if face.data.starts_with(&[0, 1, 0, 0]) { "truetype" } else { "opentype" };
        css.push_str(&format!(
            "@font-face{{font-family:\"{}\";font-weight:{weight};font-style:{style};src:url(\"fonts/{}\") format(\"{format}\");}}\n",
            face.family,
            font_file_name(face)
        ));
    }
    css
}

fn font_file_name(face: &Face) -> String {
    let mut name: String = face.family.chars().map(|ch| if ch.is_ascii_alphanumeric() { ch } else { '-' }).collect();
    if name.is_empty() {
        name.push_str("font");
    }
    if face.bold {
        name.push_str("-700");
    }
    if face.italic {
        name.push_str("-italic");
    }
    name.push_str(if face.data.starts_with(&[0, 1, 0, 0]) { ".ttf" } else { ".otf" });
    name
}

fn page_file(index: usize) -> String {
    format!("page-{:03}.xhtml", index + 1)
}

fn page_href(page: usize, count: usize) -> String {
    let index = if count == 0 { 0 } else { page.min(count - 1) };
    page_file(index)
}

fn xml(text: &str) -> String {
    let mut out = String::new();
    for ch in text.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            ch if matches!(ch, '\t' | '\n' | '\r' | '\u{20}'..='\u{D7FF}' | '\u{E000}'..='\u{FFFD}') => out.push(ch),
            _ => {}
        }
    }
    out
}

fn num(value: f32) -> String {
    format!("{value:.0}")
}

fn simple_hash(text: &str) -> u32 {
    text.bytes().fold(2166136261u32, |hash, byte| hash.wrapping_mul(16777619) ^ byte as u32)
}

fn modified_now() -> String {
    let secs = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let days = secs / 86400;
    let time = secs % 86400;
    let (year, month, day) = civil_date(days);
    format!("{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}Z", time / 3600, (time % 3600) / 60, time % 60)
}

fn civil_date(mut days: u64) -> (i32, u32, u32) {
    days += 719468;
    let era = days / 146097;
    let doe = days % 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let year = yoe as i32 + era as i32 * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = if month <= 2 { year + 1 } else { year };
    (year, month as u32, day as u32)
}

const CONTAINER: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\"><rootfiles><rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/></rootfiles></container>\n";
