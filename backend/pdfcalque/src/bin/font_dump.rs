use lopdf::Document;

fn main() {
    let path = std::env::args().nth(1).expect("pdf");
    let doc = Document::load(&path).expect("load");
    let pages = doc.get_pages();
    println!("pages {}", pages.len());
    let Some(id) = pages.get(&9).or_else(|| pages.values().next()) else {
        println!("no page");
        return;
    };
    let fonts = doc.get_page_fonts(*id).unwrap_or_default();
    println!("fonts {}", fonts.len());
    for (name, dict) in fonts {
        let keys: Vec<String> = dict.iter().map(|(k, _)| String::from_utf8_lossy(k).into_owned()).collect();
        println!("FONT {} keys {keys:?}", String::from_utf8_lossy(&name));
        for key in [b"Subtype".as_slice(), b"BaseFont", b"Encoding"] {
            if let Ok(value) = dict.get(key) {
                println!("  {} = {value:?}", String::from_utf8_lossy(key));
            }
        }
        if let Ok(desc) = dict.get(b"FontDescriptor").and_then(|obj| match obj {
            lopdf::Object::Reference(id) => doc.get_dictionary(*id),
            lopdf::Object::Dictionary(d) => Ok(d),
            _ => Err(lopdf::Error::DictKey("FontDescriptor".into())),
        }) {
            let keys: Vec<String> = desc.iter().map(|(k, _)| String::from_utf8_lossy(k).into_owned()).collect();
            println!("  DESC {keys:?}");
            for key in [b"FontFile".as_slice(), b"FontFile2", b"FontFile3"] {
                if let Ok(obj) = desc.get(key) {
                    let stream = match obj {
                        lopdf::Object::Stream(s) => Some(s),
                        lopdf::Object::Reference(id) => doc.get_object(*id).ok().and_then(|o| o.as_stream().ok()),
                        _ => None,
                    };
                    if let Some(stream) = stream {
                        let subtype = stream.dict.get(b"Subtype").ok().map(|v| format!("{v:?}")).unwrap_or_default();
                        let data = stream.decompressed_content().unwrap_or_else(|_| stream.content.clone());
                        println!("  {} bytes {} subtype {subtype} head {:02x?}", String::from_utf8_lossy(key), data.len(), &data[..data.len().min(16)]);
                        let _ = std::fs::create_dir_all("target/preview/fontsrc");
                        let base = dict.get(b"BaseFont").ok().and_then(|o| o.as_name().ok()).map(|n| String::from_utf8_lossy(n).replace('+', "-")).unwrap_or_else(|| "font".into());
                        let _ = std::fs::write(format!("target/preview/fontsrc/{base}.pfb"), &data);
                    }
                }
            }
        }
        if let Ok(obj) = dict.get(b"ToUnicode") {
            let stream = match obj {
                lopdf::Object::Stream(s) => Some(s),
                lopdf::Object::Reference(id) => doc.get_object(*id).ok().and_then(|o| o.as_stream().ok()),
                _ => None,
            };
            if let Some(stream) = stream {
                let data = stream.decompressed_content().unwrap_or_else(|_| stream.content.clone());
                let text = String::from_utf8_lossy(&data[..data.len().min(600)]);
                println!("  TOUNICODE\n{text}");
            }
        }
    }
    let content = doc.get_page_content(*id).unwrap_or_default();
    let show = content.len().min(500);
    println!("CONTENT {show}\n{}", String::from_utf8_lossy(&content[..show]));
}
