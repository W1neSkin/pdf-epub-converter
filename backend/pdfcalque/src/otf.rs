//! Type 1 из PDF → OpenType (CFF), который EPUB и браузер умеют рисовать.
//!
//! Сам файл Type 1 в папку fonts класть бесполезно: читалка его не подключает.
//! Контуры те же, таблица cmap ведёт букву Юникода на тот глиф, которым её рисует PDF.

use std::collections::BTreeMap;

use stet_fonts::agl::glyph_name_to_unicode;
use stet_fonts::cff_writer::{CidFont, FontDict, Glyph, write_cid_font};
use stet_fonts::type1_parser::parse_type1;
use stet_fonts::type1_to_type2::{choose_widths, convert_charstring, Type2Glyph};

/// Собрать один OpenType из нескольких подмножеств одного шрифта.
/// `links` — буква, которую мы пишем в SVG, и имя глифа в Type 1.
pub fn from_type1(programs: &[Vec<u8>], family: &str, links: &[(char, String)]) -> Result<Vec<u8>, String> {
    let mut glyphs: Vec<(String, Type2Glyph)> = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let mut upem = 1000u16;
    let mut bbox = [-200.0, -300.0, 1200.0, 900.0];
    let mut notdef_source: Option<(Vec<Vec<u8>>, usize)> = None;
    for program in programs {
        let font = parse_type1(program).map_err(|err| err.to_string())?;
        if font.font_matrix[0].abs() > 0.000_000_1 {
            upem = (1.0 / font.font_matrix[0]).round().clamp(16.0, 16384.0) as u16;
        }
        if font.font_bbox[2] > font.font_bbox[0] {
            bbox = font.font_bbox;
        }
        if notdef_source.is_none() {
            notdef_source = Some((font.subrs.clone(), font.len_iv));
        }
        for (name, bytes) in &font.charstrings {
            if !seen.insert(name.clone()) {
                continue;
            }
            if let Ok(glyph) = convert_charstring(bytes, &font.subrs, font.len_iv) {
                glyphs.push((name.clone(), glyph));
            }
        }
    }
    if glyphs.is_empty() {
        return Err("в Type 1 нет контуров".into());
    }
    glyphs.sort_by(|a, b| a.0.cmp(&b.0));
    if glyphs[0].0 != ".notdef" {
        let (subrs, len_iv) = notdef_source.unwrap_or_else(|| (Vec::new(), 4));
        glyphs.insert(0, (".notdef".into(), blank_glyph(&subrs, len_iv)?));
    }
    let (cff, advances) = pack_cff(&glyphs)?;
    let mut cmap_pairs: BTreeMap<u16, u16> = BTreeMap::new();
    let mut gid_of: BTreeMap<&str, u16> = BTreeMap::new();
    for (gid, (name, _)) in glyphs.iter().enumerate() {
        gid_of.insert(name, gid as u16);
        if let Some(ch) = glyph_name_to_unicode(name) {
            cmap_pairs.entry(ch).or_insert(gid as u16);
        }
    }
    for (ch, name) in links {
        if let Some(gid) = gid_of.get(name.as_str()) {
            cmap_pairs.insert(*ch as u16, *gid);
        }
    }
    Ok(wrap_otf(&cff, &advances, &cmap_pairs, family, upem, bbox))
}

fn blank_glyph(subrs: &[Vec<u8>], len_iv: usize) -> Result<Type2Glyph, String> {
    // Пустой глиф: ширина 0 и endchar. Первые len_iv байт шифр выбрасывает.
    let mut plain = vec![0u8; len_iv];
    plain.extend_from_slice(&[139, 139, 13, 14]);
    convert_charstring(&encrypt_charstring(&plain), subrs, len_iv)
}

fn pack_cff(glyphs: &[(String, Type2Glyph)]) -> Result<(Vec<u8>, Vec<u16>), String> {
    let widths: Vec<f64> = glyphs.iter().map(|(_, glyph)| glyph.width).collect();
    let (default_width, nominal_width) = choose_widths(&widths);
    let mut font = CidFont::new("PDFCalque", "Adobe", "Identity", 0);
    font.cid_count = glyphs.len() as u32;
    let mut dict = FontDict::default();
    dict.private.default_width_x = default_width;
    dict.private.nominal_width_x = nominal_width;
    font.font_dicts = vec![dict];
    let mut advances = Vec::with_capacity(glyphs.len());
    for (cid, (_, glyph)) in glyphs.iter().enumerate() {
        let mut program = glyph.charstring(default_width, nominal_width)?;
        if program.last() != Some(&14) {
            program.push(14);
        }
        font.glyphs.push(Glyph::new(cid as u16, 0, program));
        advances.push(glyph.width.round().clamp(0.0, 65535.0) as u16);
    }
    Ok((write_cid_font(&font)?, advances))
}

fn wrap_otf(cff: &[u8], advances: &[u16], cmap: &BTreeMap<u16, u16>, family: &str, upem: u16, bbox: [f64; 4]) -> Vec<u8> {
    let asc = bbox[3].round().clamp(-16000.0, 16000.0) as i16;
    let desc = bbox[1].round().clamp(-16000.0, 16000.0) as i16;
    let x_min = bbox[0].round().clamp(-16000.0, 16000.0) as i16;
    let x_max = bbox[2].round().clamp(-16000.0, 16000.0) as i16;
    let num = advances.len() as u16;
    let advance_max = advances.iter().copied().max().unwrap_or(0);
    let tables = vec![
        (*b"CFF ", cff.to_vec()),
        (*b"OS/2", os2(asc, desc, advance_max)),
        (*b"cmap", cmap4(cmap)),
        (*b"head", head(upem, x_min, asc, x_max, desc)),
        (*b"hhea", hhea(asc, desc, advance_max, num)),
        (*b"hmtx", hmtx(advances)),
        (*b"maxp", maxp(num)),
        (*b"name", name_table(family)),
        (*b"post", post()),
    ];
    let mut font = assemble(&tables);
    let sum = checksum(&font);
    let adjust = 0xB1B0_AFBAu32.wrapping_sub(sum);
    // В head поле checkSumAdjustment лежит по смещению 8.
    let head_off = table_offset(&font, b"head").unwrap() + 8;
    font[head_off..head_off + 4].copy_from_slice(&adjust.to_be_bytes());
    font
}

fn assemble(tables: &[([u8; 4], Vec<u8>)]) -> Vec<u8> {
    let count = tables.len() as u16;
    let (search, entry, shift) = search_header(count);
    let mut dir = Vec::new();
    push_u32(&mut dir, 0x4F54_544F);
    push_u16(&mut dir, count);
    push_u16(&mut dir, search);
    push_u16(&mut dir, entry);
    push_u16(&mut dir, shift);
    // Каталог таблиц занимает 16 байт на таблицу и начинается сразу после 12-байтного заголовка.
    let mut cursor = dir.len() + tables.len() * 16;
    let mut records = Vec::new();
    let mut body = Vec::new();
    for (tag, data) in tables {
        let mut padded = data.clone();
        while padded.len() % 4 != 0 {
            padded.push(0);
        }
        records.extend_from_slice(tag);
        records.extend_from_slice(&checksum(&padded).to_be_bytes());
        records.extend_from_slice(&(cursor as u32).to_be_bytes());
        records.extend_from_slice(&(data.len() as u32).to_be_bytes());
        body.extend_from_slice(&padded);
        cursor += padded.len();
    }
    dir.extend_from_slice(&records);
    dir.extend_from_slice(&body);
    dir
}

#[cfg(test)]
mod tests {
    use super::assemble;

    #[test]
    fn tables_start_after_the_directory() {
        let font = assemble(&[(*b"aaaa", vec![1, 2, 3]), (*b"bbbb", vec![4, 5, 6, 7])]);
        let start = 12 + 2 * 16;
        assert_eq!(&font[start..start + 4], &[1, 2, 3, 0]);
        assert_eq!(&font[start + 4..start + 8], &[4, 5, 6, 7]);
    }
}

fn table_offset(font: &[u8], tag: &[u8; 4]) -> Option<usize> {
    let count = u16::from_be_bytes([font[4], font[5]]) as usize;
    for index in 0..count {
        let at = 12 + index * 16;
        if &font[at..at + 4] == tag {
            return Some(u32::from_be_bytes(font[at + 8..at + 12].try_into().ok()?) as usize);
        }
    }
    None
}

fn search_header(count: u16) -> (u16, u16, u16) {
    let mut pow = 1u16;
    let mut entry = 0u16;
    while pow * 2 <= count {
        pow *= 2;
        entry += 1;
    }
    (pow * 16, entry, count * 16 - pow * 16)
}

fn checksum(data: &[u8]) -> u32 {
    let mut sum = 0u32;
    let mut index = 0;
    while index < data.len() {
        let mut word = [0u8; 4];
        let end = (index + 4).min(data.len());
        word[..end - index].copy_from_slice(&data[index..end]);
        sum = sum.wrapping_add(u32::from_be_bytes(word));
        index += 4;
    }
    sum
}

fn head(upem: u16, x_min: i16, y_max: i16, x_max: i16, y_min: i16) -> Vec<u8> {
    let mut out = vec![0u8; 54];
    out[0..2].copy_from_slice(&1u16.to_be_bytes());
    out[4..8].copy_from_slice(&0x0001_0000u32.to_be_bytes());
    out[12..16].copy_from_slice(&0x5F0F_3CF5u32.to_be_bytes());
    out[16..18].copy_from_slice(&3u16.to_be_bytes());
    out[18..20].copy_from_slice(&upem.to_be_bytes());
    put_i16(&mut out, 36, x_min);
    put_i16(&mut out, 38, y_min);
    put_i16(&mut out, 40, x_max);
    put_i16(&mut out, 42, y_max);
    out[46..48].copy_from_slice(&8u16.to_be_bytes());
    put_i16(&mut out, 48, 2);
    out
}

fn hhea(asc: i16, desc: i16, advance_max: u16, count: u16) -> Vec<u8> {
    let mut out = vec![0u8; 36];
    out[0..2].copy_from_slice(&1u16.to_be_bytes());
    put_i16(&mut out, 4, asc);
    put_i16(&mut out, 6, desc);
    out[10..12].copy_from_slice(&advance_max.to_be_bytes());
    put_i16(&mut out, 16, advance_max as i16);
    put_i16(&mut out, 18, 1);
    out[34..36].copy_from_slice(&count.to_be_bytes());
    out
}

fn hmtx(advances: &[u16]) -> Vec<u8> {
    let mut out = Vec::with_capacity(advances.len() * 4);
    for advance in advances {
        out.extend_from_slice(&advance.to_be_bytes());
        out.extend_from_slice(&0i16.to_be_bytes());
    }
    out
}

fn maxp(count: u16) -> Vec<u8> {
    let mut out = Vec::new();
    push_u32(&mut out, 0x0000_5000);
    push_u16(&mut out, count);
    out
}

fn post() -> Vec<u8> {
    let mut out = vec![0u8; 32];
    out[0..4].copy_from_slice(&0x0003_0000u32.to_be_bytes());
    put_i16(&mut out, 8, -100);
    put_i16(&mut out, 10, 50);
    out
}

fn os2(asc: i16, desc: i16, advance: u16) -> Vec<u8> {
    let mut out = vec![0u8; 96];
    out[0..2].copy_from_slice(&3u16.to_be_bytes());
    out[2..4].copy_from_slice(&advance.to_be_bytes());
    out[4..6].copy_from_slice(&400u16.to_be_bytes());
    out[6..8].copy_from_slice(&5u16.to_be_bytes());
    put_i16(&mut out, 68, asc);
    put_i16(&mut out, 70, desc);
    out[72..74].copy_from_slice(&0u16.to_be_bytes());
    out[74..76].copy_from_slice(&(asc.max(0) as u16).to_be_bytes());
    out[76..78].copy_from_slice(&(desc.min(0).unsigned_abs()).to_be_bytes());
    out[86..88].copy_from_slice(&32u16.to_be_bytes());
    out
}

fn cmap4(pairs: &BTreeMap<u16, u16>) -> Vec<u8> {
    let mut ends = Vec::new();
    let mut starts = Vec::new();
    let mut deltas = Vec::new();
    for (&code, &gid) in pairs {
        if code == 0xFFFF {
            continue;
        }
        let delta = gid as i32 - code as i32;
        if !(i16::MIN as i32..=i16::MAX as i32).contains(&delta) {
            continue;
        }
        starts.push(code);
        ends.push(code);
        deltas.push(delta as i16);
    }
    starts.push(0xFFFF);
    ends.push(0xFFFF);
    deltas.push(1);
    let seg = starts.len() as u16;
    let (search, entry, shift) = cmap_search(seg);
    let mut body = Vec::new();
    push_u16(&mut body, 4);
    push_u16(&mut body, 0);
    push_u16(&mut body, 0);
    push_u16(&mut body, seg * 2);
    push_u16(&mut body, search);
    push_u16(&mut body, entry);
    push_u16(&mut body, shift);
    for end in &ends {
        push_u16(&mut body, *end);
    }
    push_u16(&mut body, 0);
    for start in &starts {
        push_u16(&mut body, *start);
    }
    for delta in &deltas {
        body.extend_from_slice(&delta.to_be_bytes());
    }
    for _ in 0..seg {
        push_u16(&mut body, 0);
    }
    let len = body.len() as u16;
    body[2..4].copy_from_slice(&len.to_be_bytes());
    let mut out = Vec::new();
    push_u16(&mut out, 0);
    push_u16(&mut out, 1);
    push_u16(&mut out, 3);
    push_u16(&mut out, 1);
    push_u32(&mut out, 12);
    out.extend_from_slice(&body);
    out
}

fn cmap_search(seg: u16) -> (u16, u16, u16) {
    let mut pow = 1u16;
    let mut entry = 0u16;
    while pow * 2 <= seg {
        pow *= 2;
        entry += 1;
    }
    (pow * 2, entry, seg * 2 - pow * 2)
}

fn name_table(family: &str) -> Vec<u8> {
    let family = &family[..family.len().min(63)];
    let ps = family.replace(' ', "");
    let strings = [(1u16, family), (2, "Regular"), (4, family), (6, ps.as_str())];
    let mut encoded = Vec::new();
    let mut records = Vec::new();
    for (id, text) in strings {
        let start = encoded.len() as u16;
        for ch in text.encode_utf16() {
            encoded.extend_from_slice(&ch.to_be_bytes());
        }
        let len = (encoded.len() as u16) - start;
        push_u16(&mut records, 3);
        push_u16(&mut records, 1);
        push_u16(&mut records, 0x0409);
        push_u16(&mut records, id);
        push_u16(&mut records, len);
        push_u16(&mut records, start);
    }
    let count = strings.len() as u16;
    let offset = 6 + records.len() as u16;
    let mut out = Vec::new();
    push_u16(&mut out, 0);
    push_u16(&mut out, count);
    push_u16(&mut out, offset);
    out.extend_from_slice(&records);
    out.extend_from_slice(&encoded);
    out
}

fn encrypt_charstring(plain: &[u8]) -> Vec<u8> {
    let mut state = 4330u16;
    let mut out = Vec::with_capacity(plain.len());
    for &byte in plain {
        let cipher = byte ^ (state >> 8) as u8;
        out.push(cipher);
        state = (cipher as u16).wrapping_add(state).wrapping_mul(52845).wrapping_add(22719);
    }
    out
}

fn push_u16(out: &mut Vec<u8>, value: u16) {
    out.extend_from_slice(&value.to_be_bytes());
}

fn push_u32(out: &mut Vec<u8>, value: u32) {
    out.extend_from_slice(&value.to_be_bytes());
}

fn put_i16(out: &mut [u8], at: usize, value: i16) {
    out[at..at + 2].copy_from_slice(&value.to_be_bytes());
}
