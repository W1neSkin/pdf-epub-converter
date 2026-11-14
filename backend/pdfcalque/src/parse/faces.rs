//! Шрифты из PDF для папки fonts в EPUB.
//!
//! TrueType и OpenType кладутся как есть. Type 1 (так свёрстан TeX) превращается
//! в OpenType: читалка рисует только его. Подмножества одного имени склеиваются,
//! иначе у главы не хватит букв.

use std::collections::HashMap;

use lopdf::{Document as PdfFile, Object, Stream};

use crate::Face;

use super::font;

struct Group {
    family: String,
    bold: bool,
    italic: bool,
    ready: Vec<Vec<u8>>,
    type1: Vec<Vec<u8>>,
    links: Vec<(char, String)>,
}

pub fn collect(file: &PdfFile) -> Vec<Face> {
    let mut groups: HashMap<String, Group> = HashMap::new();
    for object in file.objects.values() {
        let Object::Dictionary(dict) = object else { continue };
        if dict.get(b"Type").and_then(Object::as_name).ok() != Some(b"Font".as_slice()) {
            continue;
        }
        let Some(program) = font_program(file, dict) else { continue };
        let info = font::load_font(file, object);
        let Some(family) = info.name.clone() else { continue };
        let key = format!("{family}\u{0}{}\u{0}{}", info.bold, info.italic);
        let group = groups.entry(key).or_insert_with(|| Group {
            family,
            bold: info.bold,
            italic: info.italic,
            ready: Vec::new(),
            type1: Vec::new(),
            links: Vec::new(),
        });
        if is_sfnt(&program) {
            if !group.ready.iter().any(|have| have == &program) {
                group.ready.push(program);
            }
            continue;
        }
        if group.type1.iter().any(|have| have == &program) {
            continue;
        }
        remember_links(file, dict, object, &program, &mut group.links);
        group.type1.push(program);
    }
    let mut faces = Vec::new();
    for group in groups.into_values() {
        let data = if let Some(ready) = group.ready.into_iter().max_by_key(Vec::len) {
            ready
        } else if group.type1.is_empty() {
            continue;
        } else {
            match crate::otf::from_type1(&group.type1, &group.family, &group.links) {
                Ok(data) => data,
                Err(_) => continue,
            }
        };
        faces.push(Face { family: group.family, bold: group.bold, italic: group.italic, data });
    }
    faces.sort_by(|a, b| a.family.cmp(&b.family));
    faces
}

fn remember_links(file: &PdfFile, dict: &lopdf::Dictionary, object: &Object, program: &[u8], links: &mut Vec<(char, String)>) {
    let Ok(parsed) = stet_fonts::type1_parser::parse_type1(program) else { return };
    let pdf_names = encoding_names(file, dict);
    let info = font::load_font(file, object);
    for code in 0..256u32 {
        let name = pdf_names.as_ref().and_then(|names| names.get(code as usize)).filter(|name| !name.is_empty()).cloned().or_else(|| {
            parsed.encoding.get(code as usize).filter(|name| !name.is_empty() && name.as_str() != ".notdef").cloned()
        });
        let Some(name) = name else { continue };
        let Some((text, _)) = info.glyphs(&[code as u8]).into_iter().next() else { continue };
        let mut chars = text.chars();
        let Some(ch) = chars.next() else { continue };
        if chars.next().is_some() || ch == '\u{FFFD}' {
            continue;
        }
        links.push((ch, name));
    }
}

fn encoding_names(file: &PdfFile, font: &lopdf::Dictionary) -> Option<Vec<String>> {
    let raw = font.get(b"Encoding").ok()?;
    let dict = match raw {
        Object::Dictionary(dict) => dict,
        Object::Reference(id) => file.get_dictionary(*id).ok()?,
        _ => return None,
    };
    let Object::Array(diff) = dict.get(b"Differences").ok()? else { return None };
    let mut names = vec![String::new(); 256];
    let mut code = 0usize;
    for item in diff {
        if let Ok(number) = item.as_i64() {
            code = number.max(0) as usize;
            continue;
        }
        if let Ok(name) = item.as_name() {
            if code < 256 {
                names[code] = String::from_utf8_lossy(name).into_owned();
            }
            code += 1;
        }
    }
    Some(names)
}

fn font_program(file: &PdfFile, font: &lopdf::Dictionary) -> Option<Vec<u8>> {
    let descriptor = descriptor(file, font)?;
    for key in [b"FontFile2".as_slice(), b"FontFile3", b"FontFile"] {
        let Ok(obj) = descriptor.get(key) else { continue };
        let stream = match obj {
            Object::Stream(stream) => stream,
            Object::Reference(id) => file.get_object(*id).ok().and_then(|object| object.as_stream().ok())?,
            _ => continue,
        };
        return Some(bytes(stream));
    }
    None
}

fn descriptor<'a>(file: &'a PdfFile, font: &'a lopdf::Dictionary) -> Option<&'a lopdf::Dictionary> {
    if let Some(dict) = font.get(b"FontDescriptor").ok().and_then(|obj| resolve(file, obj)) {
        return Some(dict);
    }
    let Object::Array(list) = font.get(b"DescendantFonts").ok()? else { return None };
    let child = resolve(file, list.first()?)?;
    child.get(b"FontDescriptor").ok().and_then(|obj| resolve(file, obj))
}

fn resolve<'a>(file: &'a PdfFile, obj: &'a Object) -> Option<&'a lopdf::Dictionary> {
    match obj {
        Object::Dictionary(dict) => Some(dict),
        Object::Reference(id) => file.get_dictionary(*id).ok(),
        _ => None,
    }
}

fn bytes(stream: &Stream) -> Vec<u8> {
    stream.decompressed_content().unwrap_or_else(|_| stream.content.clone())
}

fn is_sfnt(data: &[u8]) -> bool {
    data.starts_with(&[0, 1, 0, 0]) || data.starts_with(b"OTTO") || data.starts_with(b"true") || data.starts_with(b"ttcf")
}
