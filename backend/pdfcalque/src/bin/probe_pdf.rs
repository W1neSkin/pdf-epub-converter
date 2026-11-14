//! Почему у файла ноль страниц: трейлер, каталог и объекты Page.

use lopdf::{Document, Object, ObjectStream};

fn main() {
    let path = std::env::args().nth(1).expect("pdf");
    let doc = match Document::load(&path) {
        Ok(doc) => doc,
        Err(err) => {
            println!("LOAD {err}");
            return;
        }
    };
    println!("objects {}", doc.objects.len());
    println!("pages {}", doc.get_pages().len());
    let keys: Vec<String> = doc.trailer.iter().map(|(k, _)| String::from_utf8_lossy(k).into_owned()).collect();
    println!("trailer {keys:?}");
    match doc.catalog() {
        Ok(cat) => {
            let keys: Vec<String> = cat.iter().map(|(k, _)| String::from_utf8_lossy(k).into_owned()).collect();
            println!("catalog {keys:?}");
            println!("Pages {:?}", cat.get(b"Pages"));
        }
        Err(err) => println!("catalog error {err}"),
    }
    let mut page_like = 0;
    let mut types = std::collections::BTreeMap::<String, usize>::new();
    for object in doc.objects.values() {
        let dict = match object {
            Object::Dictionary(dict) => dict,
            Object::Stream(stream) => &stream.dict,
            _ => continue,
        };
        if let Ok(kind) = dict.get(b"Type").and_then(Object::as_name) {
            let name = String::from_utf8_lossy(kind).into_owned();
            *types.entry(name.clone()).or_default() += 1;
            if name == "Page" || name == "Pages" {
                page_like += 1;
            }
        }
    }
    println!("page-like {page_like}");
    println!("types {types:?}");
    let mut normal = 0;
    let mut compressed = 0;
    let mut free = 0;
    for entry in doc.reference_table.entries.values() {
        match entry {
            lopdf::xref::XrefEntry::Normal { .. } => normal += 1,
            lopdf::xref::XrefEntry::Compressed { .. } => compressed += 1,
            _ => free += 1,
        }
    }
    let mut doc = doc;
    let ids: Vec<_> = doc.objects.keys().copied().collect();
    let mut recovered = Vec::new();
    for id in ids {
        let Some(Object::Stream(stream)) = doc.objects.get_mut(&id) else { continue };
        if stream.dict.get(b"Type").and_then(Object::as_name).ok() != Some(b"ObjStm".as_slice()) { continue }
        let first = stream.dict.get(b"First").and_then(Object::as_i64).unwrap_or(0).max(0) as usize;
        let end = first.min(stream.content.len());
        for byte in &mut stream.content[..end] { if *byte == 0 { *byte = b' '; } }
        if let Ok(parsed) = ObjectStream::new(stream) { recovered.extend(parsed.objects); }
    }
    for (id, object) in recovered { doc.objects.entry(id).or_insert(object); }
    println!("pages_after {}", doc.get_pages().len());
    println!("has_catalog {}", doc.catalog().is_ok());
    println!("xref normal={normal} compressed={compressed} free={free} entry1={:?}", doc.reference_table.get(1));
    let mut failed = 0;
    let mut recovered = 0;
    for (id, object) in &doc.objects {
        let Object::Stream(stream) = object else { continue };
        if stream.dict.get(b"Type").and_then(Object::as_name).ok() != Some(b"ObjStm".as_slice()) {
            continue;
        }
        if id.0 == 2 {
            println!("dict {:?}", stream.dict);
            let head = String::from_utf8_lossy(&stream.content[..stream.content.len().min(180)]);
            println!("head {head:?}");
        }
        let mut stream = stream.clone();
        match ObjectStream::new(&mut stream) {
            Ok(parsed) => {
                recovered += parsed.objects.len();
                if parsed.objects.contains_key(&(1, 0)) {
                    println!("object 1 is inside stream {} 0", id.0);
                }
            }
            Err(err) => {
                failed += 1;
                println!("ObjStm {} 0 failed: {err}", id.0);
            }
        }
    }
    println!("objstm recovered_objects={recovered} failed_streams={failed}");
}
