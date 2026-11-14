//! Факсимильное сжатие CCITT из PDF. На выходе серые пиксели, 0 — чёрный.

use lopdf::{Dictionary, Object};

/// Раскодировать CCITTFaxDecode. `k < 0` — Group 4, иначе Group 3.
pub fn decode(data: &[u8], width: u32, height: u32, k: i32, black_is_1: bool) -> Option<Vec<u8>> {
    if width == 0 || height == 0 || data.is_empty() {
        return None;
    }
    let mut rows = Vec::new();
    let mut push = |transitions: &[u32]| {
        for pel in fax::decoder::pels(transitions, width) {
            // Декодер отдаёт цвет чернил. BlackIs1 меняет только смысл бита в PDF, не рисунок.
            let _ = black_is_1;
            rows.push(if pel == fax::Color::Black { 0 } else { 255 });
        }
    };
    let decoded = if k < 0 {
        fax::decoder::decode_g4(data.iter().copied(), width, Some(height), &mut push).is_some()
    } else {
        fax::decoder::decode_g3(data.iter().copied(), &mut push).is_some()
    };
    if !decoded || rows.is_empty() {
        return None;
    }
    let need = width as usize * height as usize;
    rows.truncate(need);
    if rows.len() < need {
        rows.resize(need, 255);
    }
    Some(rows)
}

pub fn parms(dict: &Dictionary) -> (i32, bool) {
    let Some(parms) = parm_dict(dict) else { return (0, false) };
    let k = parms.get(b"K").and_then(Object::as_i64).unwrap_or(0) as i32;
    let black_is_1 = parms.get(b"BlackIs1").and_then(Object::as_bool).unwrap_or(false);
    (k, black_is_1)
}

fn parm_dict(dict: &Dictionary) -> Option<&Dictionary> {
    match dict.get(b"DecodeParms").ok()? {
        Object::Dictionary(parms) => Some(parms),
        Object::Array(items) => items.iter().find_map(|item| match item {
            Object::Dictionary(parms) => Some(parms),
            _ => None,
        }),
        _ => None,
    }
}
