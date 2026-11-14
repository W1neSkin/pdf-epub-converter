//! Закладки PDF. Кроме страницы запоминаем вертикаль: две главы на одном
//! длинном листе должны открываться в разных местах, а не обе сверху.

use std::collections::HashMap;

use lopdf::{decode_text_string, Dictionary, Document as PdfFile, Object, ObjectId};

use crate::Heading;

struct PageGeom {
    index: usize,
    lly: f32,
    height: f32,
}

pub fn headings_from(file: &PdfFile) -> Vec<Heading> {
    let Ok(catalog) = file.catalog() else { return Vec::new() };
    let Ok(outlines) = file.get_dict_in_dict(catalog, b"Outlines") else { return Vec::new() };
    let Ok(first) = file.get_dict_in_dict(outlines, b"First") else { return Vec::new() };
    let named = named_destinations(file, catalog);
    let pages = page_geom(file);
    siblings(file, first, &pages, &named)
}

fn siblings(file: &PdfFile, first: &Dictionary, pages: &HashMap<ObjectId, PageGeom>, named: &HashMap<Vec<u8>, Vec<Object>>) -> Vec<Heading> {
    let mut list = Vec::new();
    let mut current = Some(first);
    while let Some(item) = current {
        if let Some(heading) = one(file, item, pages, named) {
            list.push(heading);
        }
        current = file.get_dict_in_dict(item, b"Next").ok();
    }
    list
}

fn one(file: &PdfFile, item: &Dictionary, pages: &HashMap<ObjectId, PageGeom>, named: &HashMap<Vec<u8>, Vec<Object>>) -> Option<Heading> {
    let title = item.get(b"Title").ok().map(|object| title_text(file, object)).unwrap_or_default();
    if title.is_empty() {
        return None;
    }
    let (page, y) = dest_of(file, item, pages, named).unwrap_or((0, None));
    let children = match file.get_dict_in_dict(item, b"First") {
        Ok(first) => siblings(file, first, pages, named),
        Err(_) => Vec::new(),
    };
    Some(Heading { title, page, y, children })
}

fn title_text(file: &PdfFile, object: &Object) -> String {
    match object {
        Object::Reference(id) => file.get_object(*id).ok().and_then(|object| decode_text_string(object).ok()).unwrap_or_default(),
        other => decode_text_string(other).unwrap_or_default(),
    }
}

fn dest_of(file: &PdfFile, item: &Dictionary, pages: &HashMap<ObjectId, PageGeom>, named: &HashMap<Vec<u8>, Vec<Object>>) -> Option<(usize, Option<f32>)> {
    let raw = item.get(b"Dest").ok().or_else(|| action_dest(file, item))?;
    let array = dest_array(file, raw, named)?;
    place(&array, pages)
}

fn action_dest<'a>(file: &'a PdfFile, item: &'a Dictionary) -> Option<&'a Object> {
    file.get_dict_in_dict(item, b"A").ok().and_then(|action| action.get(b"D").ok())
}

fn dest_array(file: &PdfFile, raw: &Object, named: &HashMap<Vec<u8>, Vec<Object>>) -> Option<Vec<Object>> {
    match raw {
        Object::Array(items) => Some(items.clone()),
        Object::Reference(id) => dest_array(file, file.get_object(*id).ok()?, named),
        Object::Dictionary(dict) => {
            let inner = dict.get(b"D").ok()?;
            dest_array(file, inner, named)
        }
        Object::String(bytes, _) | Object::Name(bytes) => named.get(bytes).cloned(),
        _ => None,
    }
}

fn place(array: &[Object], pages: &HashMap<ObjectId, PageGeom>) -> Option<(usize, Option<f32>)> {
    let id = array.first()?.as_reference().ok()?;
    let geom = pages.get(&id)?;
    let kind = array.get(1).and_then(|object| object.as_name().ok()).unwrap_or(b"");
    // /XYZ left top zoom, /FitH top, /FitR left bottom right top.
    let top = match kind {
        b"XYZ" => array.get(3).and_then(real),
        b"FitH" | b"FitBH" => array.get(2).and_then(real),
        b"FitR" => array.get(5).and_then(real),
        _ => None,
    };
    let y = top.map(|pdf_y| (geom.height - (pdf_y - geom.lly)).max(0.0));
    Some((geom.index, y))
}

fn real(object: &Object) -> Option<f32> {
    object.as_float().ok()
}

fn page_geom(file: &PdfFile) -> HashMap<ObjectId, PageGeom> {
    file.get_pages()
        .into_iter()
        .map(|(number, id)| {
            let (_llx, lly, _urx, ury) = super::page::page_box(file, id);
            (id, PageGeom { index: (number as usize).saturating_sub(1), lly, height: (ury - lly).abs() })
        })
        .collect()
}

fn named_destinations(file: &PdfFile, catalog: &Dictionary) -> HashMap<Vec<u8>, Vec<Object>> {
    let mut map = HashMap::new();
    if let Ok(dests) = file.get_dict_in_dict(catalog, b"Dests") {
        for (key, value) in dests.iter() {
            if let Some(array) = dest_array(file, value, &HashMap::new()) {
                map.insert(key.clone(), array);
            }
        }
    }
    if let Ok(names) = file.get_dict_in_dict(catalog, b"Names") {
        if let Ok(dests) = file.get_dict_in_dict(names, b"Dests") {
            name_tree(file, dests, &mut map);
        }
    }
    map
}

fn name_tree(file: &PdfFile, node: &Dictionary, map: &mut HashMap<Vec<u8>, Vec<Object>>) {
    if let Ok(Object::Array(kids)) = node.get(b"Kids") {
        for kid in kids {
            if let Ok(dict) = dict_of(file, kid) {
                name_tree(file, dict, map);
            }
        }
    }
    if let Ok(Object::Array(names)) = node.get(b"Names") {
        let mut index = 0;
        while index + 1 < names.len() {
            if let Ok(key) = names[index].as_str() {
                if let Some(array) = dest_array(file, &names[index + 1], &HashMap::new()) {
                    map.insert(key.to_vec(), array);
                }
            }
            index += 2;
        }
    }
}

fn dict_of<'a>(file: &'a PdfFile, object: &'a Object) -> lopdf::Result<&'a Dictionary> {
    match object {
        Object::Dictionary(dict) => Ok(dict),
        Object::Reference(id) => file.get_dictionary(*id),
        _ => Err(lopdf::Error::ObjectType { expected: "Dictionary", found: object.enum_variant() }),
    }
}
