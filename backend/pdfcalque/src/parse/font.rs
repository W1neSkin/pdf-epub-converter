//! Шрифт страницы: имя, ширины глифов и соответствие кодов буквам.
//! Ширина нужна, чтобы следующая буква встала туда же, куда её ставит PDF.

use std::collections::HashMap;

use lopdf::{Document as PdfFile, Object};

#[derive(Clone, Debug)]
pub struct FontInfo {
    pub name: Option<String>,
    pub bold: bool,
    pub italic: bool,
    wide: bool,
    first_char: u32,
    widths: Vec<f32>,
    missing: f32,
    /// Буквы TeX-шрифта без рабочей таблицы Юникода записаны в Windows-1251.
    cp1251: bool,
    ranges: Vec<(u32, u32, f32)>,
    singles: HashMap<u32, f32>,
    cmap: HashMap<(u32, u8), String>,
}

impl FontInfo {
    pub fn fallback() -> Self {
        Self {
            name: None,
            bold: false,
            italic: false,
            wide: false,
            first_char: 0,
            widths: Vec::new(),
            missing: 500.0,
            cp1251: false,
            ranges: Vec::new(),
            singles: HashMap::new(),
            cmap: HashMap::new(),
        }
    }

    /// Буква и ширина в тысячных em. Несколько байт одного кода CID дают одну запись.
    pub fn glyphs(&self, bytes: &[u8]) -> Vec<(String, f32)> {
        let mut out = Vec::new();
        let mut i = 0;
        while i < bytes.len() {
            if self.wide && i + 1 < bytes.len() {
                let code = ((bytes[i] as u32) << 8) | bytes[i + 1] as u32;
                let text = if let Some(mapped) = self.cmap.get(&(code, 2)) {
                    mapped.clone()
                } else if self.cmap.is_empty() {
                    char::from_u32(code).map(|ch| ch.to_string()).unwrap_or_else(|| "\u{FFFD}".into())
                } else {
                    "\u{FFFD}".into()
                };
                out.push((text, self.width(code)));
                i += 2;
                continue;
            }
            let code = bytes[i] as u32;
            let text = self.cmap.get(&(code, 1)).cloned().unwrap_or_else(|| {
                if self.cp1251 { cp1251(bytes[i]) } else { winansi(bytes[i]) }.to_string()
            });
            out.push((text, self.width(code)));
            i += 1;
        }
        out
    }

    fn width(&self, code: u32) -> f32 {
        if let Some(width) = self.singles.get(&code) {
            return *width;
        }
        for (start, end, width) in &self.ranges {
            if code >= *start && code <= *end {
                return *width;
            }
        }
        let index = code.wrapping_sub(self.first_char) as usize;
        self.widths.get(index).copied().unwrap_or(self.missing)
    }
}

pub fn load_font(doc: &PdfFile, object: &Object) -> FontInfo {
    let Some(dict) = resolve_dict(doc, object) else {
        return FontInfo::fallback();
    };
    let mut font = FontInfo::fallback();
    if let Some(base) = name_of(dict.get(b"BaseFont").ok()) {
        font.bold = base.contains("Bold");
        font.italic = base.contains("Italic") || base.contains("Oblique");
        font.name = Some(strip_subset(&base));
    }
    font.wide = dict.get(b"Subtype").and_then(Object::as_name).ok() == Some(b"Type0".as_slice());
    if let Some(desc) = descendant(doc, dict) {
        read_cid_widths(doc, desc, &mut font);
        if font.name.is_none() {
            font.name = name_of(desc.get(b"BaseFont").ok()).map(|name| strip_subset(&name));
        }
    }
    if let Ok(first) = dict.get(b"FirstChar").and_then(Object::as_i64) {
        font.first_char = first as u32;
    }
    if let Ok(Object::Array(widths)) = dict.get(b"Widths") {
        font.widths = widths.iter().map(number).collect();
    }
    if let Some(descriptor) = dict.get(b"FontDescriptor").ok().and_then(|obj| resolve_dict(doc, obj)) {
        if let Ok(flags) = descriptor.get(b"Flags").and_then(Object::as_i64) {
            // Биты из PDF: 7 — курсив, 19 — жирный.
            font.italic = font.italic || flags & (1 << 6) != 0;
            font.bold = font.bold || flags & (1 << 18) != 0;
        }
        if let Ok(missing) = descriptor.get(b"MissingWidth").and_then(Object::as_float) {
            font.missing = missing;
        }
    }
    if let Some(stream) = dict.get(b"ToUnicode").ok().and_then(|obj| resolve_stream(doc, obj)) {
        let map = parse_tounicode(&stream);
        // У шрифтов TeX T2A таблица иногда указывает все коды на цифру «1» и латиницу.
        // Тогда буквы берём из Windows-1251: байты страницы совпадают с ней.
        // У испорченной таблицы TeX почти нет настоящих русских букв, хотя кодов много.
        let broken = degenerate(&map) || (font.name.as_deref().is_some_and(tex_cyrillic) && cyrillic_letters(&map) < 20);
        if !broken {
            font.cmap = map;
            if font.cmap.keys().any(|(_, len)| *len > 1) {
                font.wide = true;
            }
        }
    }
    font.cp1251 = font.cmap.is_empty() && font.name.as_deref().is_some_and(tex_cyrillic);
    font
}

fn cyrillic_letters(map: &HashMap<(u32, u8), String>) -> usize {
    let mut seen = std::collections::HashSet::new();
    for text in map.values() {
        for ch in text.chars() {
            if ('\u{0400}'..='\u{04FF}').contains(&ch) {
                seen.insert(ch);
            }
        }
    }
    seen.len()
}

fn degenerate(map: &HashMap<(u32, u8), String>) -> bool {
    if map.len() < 16 {
        return false;
    }
    let mut counts = HashMap::<&str, usize>::new();
    for value in map.values() {
        *counts.entry(value).or_insert(0) += 1;
    }
    counts.values().copied().max().unwrap_or(0) * 2 > map.len()
}

fn tex_cyrillic(name: &str) -> bool {
    let name = name.rsplit('+').next().unwrap_or(name);
    name.starts_with("SF") && name.len() >= 4
}

fn read_cid_widths(doc: &PdfFile, desc: &lopdf::Dictionary, font: &mut FontInfo) {
    let Ok(Object::Array(items)) = desc.get(b"W") else { return };
    let mut index = 0;
    while index < items.len() {
        let Some(start) = items.get(index).map(number).map(|n| n as u32) else { break };
        match items.get(index + 1) {
            Some(Object::Array(list)) => {
                for (offset, item) in list.iter().enumerate() {
                    font.singles.insert(start + offset as u32, number(item));
                }
                index += 2;
            }
            Some(_) if index + 2 < items.len() => {
                let end = number(&items[index + 1]) as u32;
                font.ranges.push((start, end, number(&items[index + 2])));
                index += 3;
            }
            _ => break,
        }
    }
    let _ = doc;
}

fn descendant<'a>(doc: &'a PdfFile, font: &'a lopdf::Dictionary) -> Option<&'a lopdf::Dictionary> {
    let Object::Array(list) = font.get(b"DescendantFonts").ok()? else { return None };
    resolve_dict(doc, list.first()?)
}

fn parse_tounicode(data: &[u8]) -> HashMap<(u32, u8), String> {
    let text = String::from_utf8_lossy(data);
    let mut map = HashMap::new();
    let mut mode = 0u8;
    for raw in text.lines() {
        let line = raw.trim();
        // В файле это «20 beginbfchar», число и слово на одной строке.
        if line.contains("beginbfchar") {
            mode = 1;
            continue;
        }
        if line.contains("endbfchar") || line.contains("endbfrange") {
            mode = 0;
            continue;
        }
        if line.contains("beginbfrange") {
            mode = 2;
            continue;
        }
        let tokens = hex_tokens(line);
        if mode == 1 && tokens.len() >= 2 {
            map.insert((tokens[0].0, tokens[0].1), decode_utf16(&tokens[1].2));
        }
        if mode == 2 && tokens.len() >= 3 && !line.contains('[') {
            let (start, len, _) = &tokens[0];
            let end = tokens[1].0;
            if *start > end || end - *start > 10_000 {
                continue;
            }
            let dest = u32_from_hex(&tokens[2].2);
            for code in *start..=end {
                let point = dest + (code - start);
                if let Some(ch) = char::from_u32(point) {
                    map.insert((code, *len), ch.to_string());
                }
            }
        }
    }
    map
}

fn hex_tokens(line: &str) -> Vec<(u32, u8, Vec<u8>)> {
    let bytes = line.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'<' {
            if let Some(end) = bytes[i + 1..].iter().position(|b| *b == b'>') {
                let hex = &bytes[i + 1..i + 1 + end];
                let decoded = decode_hex(hex);
                let code = decoded.iter().fold(0u32, |acc, byte| (acc << 8) | *byte as u32);
                out.push((code, decoded.len() as u8, decoded));
                i += end + 2;
                continue;
            }
        }
        i += 1;
    }
    out
}

fn decode_hex(hex: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut i = 0;
    while i + 1 < hex.len() {
        let hi = hex_val(hex[i]);
        let lo = hex_val(hex[i + 1]);
        out.push((hi << 4) | lo);
        i += 2;
    }
    out
}

fn hex_val(byte: u8) -> u8 {
    match byte {
        b'0'..=b'9' => byte - b'0',
        b'a'..=b'f' => byte - b'a' + 10,
        b'A'..=b'F' => byte - b'A' + 10,
        _ => 0,
    }
}

fn decode_utf16(bytes: &[u8]) -> String {
    let units: Vec<u16> = bytes.chunks(2).filter(|c| c.len() == 2).map(|c| u16::from_be_bytes([c[0], c[1]])).collect();
    String::from_utf16(&units).unwrap_or_else(|_| "\u{FFFD}".into())
}

fn u32_from_hex(bytes: &[u8]) -> u32 {
    bytes.iter().fold(0u32, |acc, byte| (acc << 8) | *byte as u32)
}

fn number(object: &Object) -> f32 {
    match object {
        Object::Integer(value) => *value as f32,
        Object::Real(value) => *value,
        _ => 0.0,
    }
}

fn name_of(object: Option<&Object>) -> Option<String> {
    let bytes = object?.as_name().ok()?;
    Some(String::from_utf8_lossy(bytes).into_owned())
}

fn strip_subset(name: &str) -> String {
    let bytes = name.as_bytes();
    if bytes.len() > 7 && bytes[6] == b'+' && bytes[..6].iter().all(|b| b.is_ascii_uppercase()) {
        name[7..].to_string()
    } else {
        name.to_string()
    }
}

pub fn resolve_dict<'a>(doc: &'a PdfFile, object: &'a Object) -> Option<&'a lopdf::Dictionary> {
    match object {
        Object::Dictionary(dict) => Some(dict),
        Object::Reference(id) => doc.get_object(*id).ok()?.as_dict().ok(),
        _ => None,
    }
}

fn resolve_stream(doc: &PdfFile, object: &Object) -> Option<Vec<u8>> {
    let stream = match object {
        Object::Stream(stream) => stream,
        Object::Reference(id) => doc.get_object(*id).ok()?.as_stream().ok()?,
        _ => return None,
    };
    stream.decompressed_content().ok().or_else(|| Some(stream.content.clone()))
}

fn cp1251(byte: u8) -> char {
    if (0xC0..=0xFF).contains(&byte) {
        return char::from_u32(0x0410 + byte as u32 - 0xC0).unwrap();
    }
    match byte {
        0xA8 => '\u{0401}',
        0xB8 => '\u{0451}',
        // В шрифте TeX T2A «ё» и ёлочки стоят не там, где в Windows-1251.
        0xBC => '\u{0451}',
        0xBE => '\u{00AB}',
        0xBF => '\u{00BB}',
        0xB9 => '\u{2116}',
        0xAB => '\u{00AB}',
        0xBB => '\u{00BB}',
        0x96 => '\u{2013}',
        0x97 => '\u{2014}',
        _ => winansi(byte),
    }
}

fn winansi(byte: u8) -> char {
    match byte {
        0x80 => '\u{20AC}',
        0x82 => '\u{201A}',
        0x83 => '\u{0192}',
        0x84 => '\u{201E}',
        0x85 => '\u{2026}',
        0x86 => '\u{2020}',
        0x87 => '\u{2021}',
        0x88 => '\u{02C6}',
        0x89 => '\u{2030}',
        0x8A => '\u{0160}',
        0x8B => '\u{2039}',
        0x8C => '\u{0152}',
        0x8E => '\u{017D}',
        0x91 => '\u{2018}',
        0x92 => '\u{2019}',
        0x93 => '\u{201C}',
        0x94 => '\u{201D}',
        0x95 => '\u{2022}',
        0x96 => '\u{2013}',
        0x97 => '\u{2014}',
        0x98 => '\u{02DC}',
        0x99 => '\u{2122}',
        0x9A => '\u{0161}',
        0x9B => '\u{203A}',
        0x9C => '\u{0153}',
        0x9E => '\u{017E}',
        0x9F => '\u{0178}',
        _ => char::from_u32(byte as u32).unwrap_or('\u{FFFD}'),
    }
}
