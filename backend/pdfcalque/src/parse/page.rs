//! Страницы документа: видимая рамка, ресурсы и запуск интерпретатора.

use std::collections::HashMap;

use lopdf::{Document as PdfFile, Object, ObjectId};

use crate::{Document, Element, Page};

use super::exec;
use super::font::{self, FontInfo};
use super::group;

pub fn parse_file(doc: &PdfFile) -> Result<Document, String> {
    parse_some(doc, None)
}

pub(super) fn parse_some(doc: &PdfFile, only: Option<u32>) -> Result<Document, String> {
    let mut pages = Vec::new();
    for (number, id) in doc.get_pages() {
        if only.is_some_and(|want| want != number) {
            continue;
        }
        let (llx, lly, urx, ury) = page_box(doc, id);
        let levels = resource_levels(doc, id);
        let mut fonts = HashMap::<Vec<u8>, FontInfo>::new();
        exec::load_fonts_into(doc, &levels, &mut fonts);
        // Между потоками нужен разделитель, иначе конец одного и начало другого
        // слипаются в одну команду, например Q и q становятся «Qq».
        let data = page_content(doc, id)?;
        let paints = exec::execute(doc, &levels, &fonts, &data, super::matrix::Matrix::identity(), 0)
            .map_err(|err| format!("page {number}: {err}"))?;
        let mut elements = group::group(paints);
        shift(&mut elements, -llx, -lly);
        let width = (urx - llx).abs();
        let height = (ury - lly).abs();
        crate::ocr::maybe_scan(&mut elements, width, height);
        pages.push(Page { width, height, elements });
    }
    Ok(Document { pages, title: String::new(), language: String::new(), outline: Vec::new(), faces: Vec::new() })
}

pub(super) fn page_box(doc: &PdfFile, page_id: ObjectId) -> (f32, f32, f32, f32) {
    let mut crop = None;
    let mut media = None;
    let mut current = page_id;
    for _ in 0..32 {
        let Ok(dict) = doc.get_dictionary(current) else { break };
        if crop.is_none() {
            crop = rect_of(dict, b"CropBox");
        }
        if media.is_none() {
            media = rect_of(dict, b"MediaBox");
        }
        let Ok(parent) = dict.get(b"Parent").and_then(Object::as_reference) else { break };
        current = parent;
    }
    crop.or(media).unwrap_or((0.0, 0.0, 612.0, 792.0))
}

fn rect_of(dict: &lopdf::Dictionary, key: &[u8]) -> Option<(f32, f32, f32, f32)> {
    let Object::Array(items) = dict.get(key).ok()? else { return None };
    if items.len() < 4 {
        return None;
    }
    Some((num(&items[0]), num(&items[1]), num(&items[2]), num(&items[3])))
}

fn resource_levels<'a>(doc: &'a PdfFile, page_id: ObjectId) -> Vec<&'a lopdf::Dictionary> {
    let mut ids = vec![page_id];
    let mut current = page_id;
    for _ in 0..32 {
        let Ok(dict) = doc.get_dictionary(current) else { break };
        let Ok(parent) = dict.get(b"Parent").and_then(Object::as_reference) else { break };
        ids.push(parent);
        current = parent;
    }
    ids.into_iter()
        .filter_map(|id| {
            let dict = doc.get_dictionary(id).ok()?;
            dict.get(b"Resources").ok().and_then(|obj| font::resolve_dict(doc, obj))
        })
        .collect()
}

fn page_content(doc: &PdfFile, page_id: ObjectId) -> Result<Vec<u8>, String> {
    let mut content = Vec::new();
    for object_id in doc.get_page_contents(page_id) {
        let stream = doc
            .get_object(object_id)
            .and_then(Object::as_stream)
            .map_err(|err| err.to_string())?;
        let data = stream.decompressed_content().unwrap_or_else(|_| stream.content.clone());
        if !content.is_empty() {
            content.push(b'\n');
        }
        content.extend_from_slice(&data);
    }
    Ok(content)
}

fn num(object: &Object) -> f32 {
    match object {
        Object::Integer(value) => *value as f32,
        Object::Real(value) => *value,
        _ => 0.0,
    }
}

fn shift(elements: &mut [Element], dx: f32, dy: f32) {
    if dx == 0.0 && dy == 0.0 {
        return;
    }
    for element in elements {
        shift_one(element, dx, dy);
    }
}

fn shift_one(element: &mut Element, dx: f32, dy: f32) {
    match element {
        Element::Text(block) => {
            move_rect(&mut block.bounds, dx, dy);
            for line in &mut block.lines {
                move_rect(&mut line.bounds, dx, dy);
                for span in &mut line.spans {
                    move_rect(&mut span.bounds, dx, dy);
                    for glyph in &mut span.glyphs {
                        move_rect(&mut glyph.bounds, dx, dy);
                        glyph.origin.x += dx;
                        glyph.origin.y += dy;
                    }
                }
            }
        }
        Element::Image(image) => move_rect(&mut image.bounds, dx, dy),
        Element::Path(path) => {
            move_rect(&mut path.bounds, dx, dy);
            for segment in &mut path.segments {
                match segment {
                    crate::PathSegment::Move(p) | crate::PathSegment::Line(p) => { p.x += dx; p.y += dy; }
                    crate::PathSegment::Curve { c1, c2, end } => {
                        c1.x += dx; c1.y += dy; c2.x += dx; c2.y += dy; end.x += dx; end.y += dy;
                    }
                    crate::PathSegment::Close => {}
                }
            }
        }
        Element::Table(table) => {
            move_rect(&mut table.bounds, dx, dy);
            for row in &mut table.rows {
                for cell in &mut row.cells {
                    move_rect(&mut cell.bounds, dx, dy);
                    shift(&mut cell.content, dx, dy);
                }
            }
        }
    }
}

fn move_rect(rect: &mut crate::Rect, dx: f32, dy: f32) {
    rect.x += dx;
    rect.y += dy;
}
