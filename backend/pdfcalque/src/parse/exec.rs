//! Исполнение команд одной страницы или вложенной формы.
//! Состояние рисования одно: матрица, цвет, шрифт, текстовая позиция, контур.

use std::collections::HashMap;

use lopdf::content::Content;
use lopdf::{Dictionary, Document as PdfFile, Object};

use crate::geom::{Color, Point, Rect};
use crate::model::{PathSegment, PathShape};
use crate::Image;

use super::font::{self, FontInfo};
use super::matrix::Matrix;

pub struct GlyphPaint {
    pub origin: Point,
    pub text: String,
    pub font_name: Option<String>,
    pub size: f32,
    /// Поворот в градусах для SVG: 0 — строка слева направо.
    pub rotation: f32,
    pub bold: bool,
    pub italic: bool,
    pub color: Color,
    pub advance: f32,
    pub visible: bool,
}

/// Делит слипшуюся строку на известные команды. «cm» не режется, потому что это одна команда.
fn split_glued(name: &str) -> Option<Vec<&str>> {
    const KNOWN: &[&str] = &[
        "BDC", "BMC", "EMC", "scn", "SCN", "Tj", "TJ", "Td", "TD", "Tm", "Tc", "Tw", "Tz", "TL", "Tf", "Tr", "Ts", "T*",
        "rg", "RG", "cs", "CS", "sc", "SC", "re", "cm", "Do", "BT", "ET", "BI", "gs", "ri", "sh", "MP", "DP", "BX", "EX",
        "f*", "W*", "B*", "b*", "q", "Q", "w", "m", "l", "c", "v", "y", "h", "S", "s", "f", "F", "n", "W", "B", "b", "J",
        "j", "M", "d", "i", "g", "G", "k", "K",
    ];
    let mut rest = name;
    let mut parts = Vec::new();
    while !rest.is_empty() {
        let found = KNOWN.iter().find(|op| rest.starts_with(*op))?;
        parts.push(*found);
        rest = &rest[found.len()..];
    }
    (parts.len() > 1).then_some(parts)
}

fn user_point(state: &State, x: f32, y: f32) -> (f32, f32) {
    let (tx, ty) = state.text.transform(x, y);
    state.ctm.transform(tx, ty)
}

pub enum Paint {
    Glyph(GlyphPaint),
    Image(Image),
    Path(PathShape),
}

#[derive(Clone)]
struct State {
    ctm: Matrix,
    fill: Color,
    stroke: Color,
    line_width: f32,
    char_spacing: f32,
    word_spacing: f32,
    horiz: f32,
    leading: f32,
    font_key: Vec<u8>,
    font_size: f32,
    render_mode: i32,
    rise: f32,
    text: Matrix,
    line: Matrix,
}

struct Path {
    segments: Vec<PathSegment>,
    current: Point,
    start: Point,
}

pub fn execute(
    doc: &PdfFile,
    resources: &[&Dictionary],
    fonts: &HashMap<Vec<u8>, FontInfo>,
    data: &[u8],
    ctm: Matrix,
    depth: u8,
) -> Result<Vec<Paint>, String> {
    if depth > 16 {
        return Err("form nesting is too deep".into());
    }
    let content = Content::decode(data).map_err(|err| err.to_string())?;
    let mut state = State::new();
    // Вложенная форма рисуется в матрице страницы, а не с нуля.
    state.ctm = ctm;
    let mut stack = Vec::new();
    let mut path = Path::new();
    let mut paints = Vec::new();
    let mut compat = 0u32;
    for op in content.operations {
        let name = op.operator.as_str();
        if apply(doc, resources, fonts, &mut state, &mut stack, &mut path, &mut paints, &op.operands, name, depth, &mut compat)? {
            continue;
        }
        // Некоторые файлы пишут однобуквенные команды вплотную: Qq.
        if let Some(parts) = split_glued(name) {
            for part in parts {
                apply(doc, resources, fonts, &mut state, &mut stack, &mut path, &mut paints, &[], part, depth, &mut compat)?;
            }
            continue;
        }
        if compat > 0 {
            continue;
        }
        return Err(format!("unknown operator {name}"));
    }
    Ok(paints)
}

fn apply(
    doc: &PdfFile,
    resources: &[&Dictionary],
    fonts: &HashMap<Vec<u8>, FontInfo>,
    state: &mut State,
    stack: &mut Vec<State>,
    path: &mut Path,
    paints: &mut Vec<Paint>,
    args: &[Object],
    name: &str,
    depth: u8,
    compat: &mut u32,
) -> Result<bool, String> {
    let known = match name {
        "q" => { stack.push(state.clone()); true }
        "Q" => { *state = stack.pop().unwrap_or_else(State::new); true }
        "cm" => { state.ctm = Matrix::concat(matrix_from(args)?, state.ctm); true }
        "w" => { state.line_width = num_at(args, 0)?; true }
        "J" | "j" | "M" | "d" | "ri" | "i" => true,
        "gs" => { apply_ext(doc, resources, state, args)?; true }
        "g" => { state.fill = gray(num_at(args, 0)?, state.fill.a); true }
        "G" => { state.stroke = gray(num_at(args, 0)?, state.stroke.a); true }
        "rg" => { state.fill = rgb(args, state.fill.a)?; true }
        "RG" => { state.stroke = rgb(args, state.stroke.a)?; true }
        "k" => { state.fill = cmyk(args, state.fill.a)?; true }
        "K" => { state.stroke = cmyk(args, state.stroke.a)?; true }
        "cs" | "CS" => true,
        "sc" | "scn" => { state.fill = alt_color(args, state.fill); true }
        "SC" | "SCN" => { state.stroke = alt_color(args, state.stroke); true }
        "m" => { path.move_to(state.ctm, num_at(args, 0)?, num_at(args, 1)?); true }
        "l" => { path.line_to(state.ctm, num_at(args, 0)?, num_at(args, 1)?); true }
        "c" => { path.curve(state.ctm, args)?; true }
        "v" => { path.curve_v(state.ctm, args)?; true }
        "y" => { path.curve_y(state.ctm, args)?; true }
        "h" => { path.close(); true }
        "re" => { path.rect(state.ctm, args)?; true }
        "W" => true,
        "W*" => true,
        "n" => { path.clear(); true }
        "S" | "s" | "f" | "F" | "f*" | "B" | "B*" | "b" | "b*" => {
            if name == "s" || name == "b" || name == "b*" { path.close(); }
            paints.push(Paint::Path(path.paint(state, name)));
            path.clear();
            true
        }
        "BT" => { state.text = Matrix::identity(); state.line = Matrix::identity(); true }
        "ET" => true,
        "Tc" => { state.char_spacing = num_at(args, 0)?; true }
        "Tw" => { state.word_spacing = num_at(args, 0)?; true }
        "Tz" => { state.horiz = num_at(args, 0)?; true }
        "TL" => { state.leading = num_at(args, 0)?; true }
        "Tf" => { state.font_key = args.first().and_then(|obj| obj.as_name().ok()).unwrap_or_default().to_vec(); state.font_size = num_at(args, 1)?; true }
        "Tr" => { state.render_mode = num_at(args, 0)? as i32; true }
        "Ts" => { state.rise = num_at(args, 0)?; true }
        "Td" => { state.move_text(num_at(args, 0)?, num_at(args, 1)?, false)?; true }
        "TD" => { state.move_text(num_at(args, 0)?, num_at(args, 1)?, true)?; true }
        "Tm" => { let m = matrix_from(args)?; state.text = m; state.line = m; true }
        "T*" => { state.move_text(0.0, -state.leading, false)?; true }
        "Tj" | "'" | "\"" => { show(state, fonts, paints, args, name)?; true }
        "TJ" => { show_array(state, fonts, paints, args)?; true }
        "Do" => { paint_xobject(doc, resources, fonts, state, paints, args, depth)?; true }
        "BI" => { paint_inline(state, paints, args)?; true }
        "sh" => true,
        "BMC" | "BDC" | "EMC" | "MP" | "DP" => true,
        "BX" => { *compat += 1; true }
        "EX" => { *compat = compat.saturating_sub(1); true }
        _ => false,
    };
    Ok(known)
}

fn show(state: &mut State, fonts: &HashMap<Vec<u8>, FontInfo>, paints: &mut Vec<Paint>, args: &[Object], name: &str) -> Result<(), String> {
    if name == "\"" {
        state.word_spacing = num_at(args, 0)?;
        state.char_spacing = num_at(args, 1)?;
    }
    if name == "'" || name == "\"" {
        state.move_text(0.0, -state.leading, false)?;
    }
    let bytes = args.iter().rev().find_map(|obj| obj.as_str().ok()).ok_or("text operand missing")?;
    paint_string(state, fonts, paints, bytes);
    Ok(())
}

fn show_array(state: &mut State, fonts: &HashMap<Vec<u8>, FontInfo>, paints: &mut Vec<Paint>, args: &[Object]) -> Result<(), String> {
    let Some(Object::Array(items)) = args.first() else { return Err("TJ needs an array".into()) };
    for item in items {
        match item {
            Object::String(bytes, _) => paint_string(state, fonts, paints, bytes),
            Object::Integer(_) | Object::Real(_) => {
                let adjust = -num(item) / 1000.0 * state.font_size * state.horiz / 100.0;
                state.text = Matrix::concat(Matrix::translate(adjust, 0.0), state.text);
            }
            _ => {}
        }
    }
    Ok(())
}

fn paint_string(state: &mut State, fonts: &HashMap<Vec<u8>, FontInfo>, paints: &mut Vec<Paint>, bytes: &[u8]) {
    let font = fonts.get(&state.font_key).cloned().unwrap_or_else(FontInfo::fallback);
    for (text, width) in font.glyphs(bytes) {
        // Размер буквы — длина вектора em после текстовой матрицы и матрицы страницы.
        // В файле часто стоит «Tf 1» и масштаб 12 внутри Tm. Тогда видимый размер 12, не 1.
        let (x, y) = user_point(state, 0.0, state.rise);
        let em = state.font_size * state.horiz / 100.0;
        let (x_em, y_em) = user_point(state, em, state.rise);
        let size = ((x_em - x).powi(2) + (y_em - y).powi(2)).sqrt().max(0.01);
        let rotation = (y - y_em).atan2(x_em - x).to_degrees();
        let mut advance_units = width / 1000.0 * state.font_size + state.char_spacing;
        if text == " " { advance_units += state.word_spacing; }
        advance_units *= state.horiz / 100.0;
        state.text = Matrix::concat(Matrix::translate(advance_units, 0.0), state.text);
        let (x2, _) = user_point(state, 0.0, state.rise);
        paints.push(Paint::Glyph(GlyphPaint {
            origin: Point { x, y },
            advance: x2 - x,
            rotation,
            text,
            font_name: font.name.clone(),
            size,
            bold: font.bold,
            italic: font.italic,
            color: state.fill,
            visible: state.render_mode != 3,
        }));
    }
}

fn paint_xobject(doc: &PdfFile, resources: &[&Dictionary], fonts: &HashMap<Vec<u8>, FontInfo>, state: &mut State, paints: &mut Vec<Paint>, args: &[Object], depth: u8) -> Result<(), String> {
    let name = args.first().and_then(|obj| obj.as_name().ok()).ok_or("Do without a name")?;
    let object = lookup(doc, resources, b"XObject", name).ok_or("missing XObject")?;
    let stream = match object {
        Object::Stream(stream) => stream,
        Object::Reference(id) => doc.get_object(*id).and_then(Object::as_stream).map_err(|err| err.to_string())?,
        _ => return Err("XObject is not a stream".into()),
    };
    let subtype = stream.dict.get(b"Subtype").and_then(Object::as_name).unwrap_or_default();
    if subtype == b"Image" {
        paints.push(Paint::Image(image_from_stream(state, &stream.dict, &stream.content)));
        return Ok(());
    }
    if subtype == b"Form" {
        let mut child = resources.to_vec();
        if let Some(local) = stream.dict.get(b"Resources").ok().and_then(|obj| font::resolve_dict(doc, obj)) {
            child.insert(0, local);
        }
        let mut local_fonts = fonts.clone();
        if let Some(local) = child.first() {
            if child.len() > resources.len() {
                replace_fonts(doc, local, &mut local_fonts);
            }
        }
        let mut ctm = state.ctm;
        if let Ok(Object::Array(items)) = stream.dict.get(b"Matrix") {
            ctm = Matrix::concat(matrix_from(items)?, ctm);
        }
        let data = stream.decompressed_content().unwrap_or_else(|_| stream.content.clone());
        paints.extend(execute(doc, &child, &local_fonts, &data, ctm, depth + 1)?);
        return Ok(());
    }
    Err(format!("unsupported XObject {}", String::from_utf8_lossy(subtype)))
}

fn paint_inline(state: &State, paints: &mut Vec<Paint>, args: &[Object]) -> Result<(), String> {
    let Some(Object::Stream(stream)) = args.first() else { return Ok(()) };
    paints.push(Paint::Image(image_from_stream(state, &stream.dict, &stream.content)));
    Ok(())
}

fn image_from_stream(state: &State, dict: &Dictionary, data: &[u8]) -> Image {
    let corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)];
    let points: Vec<(f32, f32)> = corners.iter().map(|(x, y)| state.ctm.transform(*x, *y)).collect();
    let bounds = bounds_of(&points);
    let mut filter = filter_name(dict);
    let mut color_space = color_name(dict);
    let mut bytes = data.to_vec();
    let pixel_width = dict.get(b"Width").and_then(Object::as_i64).unwrap_or(0) as u32;
    let pixel_height = dict.get(b"Height").and_then(Object::as_i64).unwrap_or(0) as u32;
    // Факс CCITT превращаем в серые пиксели, чтобы HTML показал картинку, а не серый прямоугольник.
    if filter.contains("CCITTFaxDecode") {
        let (k, black_is_1) = crate::ccitt::parms(dict);
        if let Some(gray) = crate::ccitt::decode(&bytes, pixel_width, pixel_height, k, black_is_1) {
            bytes = gray;
            filter.clear();
            color_space = "DeviceGray".into();
        }
    }
    Image { bounds, pixel_width, pixel_height, filter, color_space, data: bytes }
}

fn apply_ext(doc: &PdfFile, resources: &[&Dictionary], state: &mut State, args: &[Object]) -> Result<(), String> {
    let Some(name) = args.first().and_then(|obj| obj.as_name().ok()) else { return Ok(()) };
    let Some(object) = lookup(doc, resources, b"ExtGState", name) else { return Ok(()) };
    let Some(dict) = font::resolve_dict(doc, object) else { return Ok(()) };
    if let Ok(alpha) = dict.get(b"ca").and_then(Object::as_float) { state.fill.a = alpha; }
    if let Ok(alpha) = dict.get(b"CA").and_then(Object::as_float) { state.stroke.a = alpha; }
    Ok(())
}

pub fn load_fonts_into(doc: &PdfFile, resources: &[&Dictionary], into: &mut HashMap<Vec<u8>, FontInfo>) {
    for level in resources {
        let Some(font_obj) = level.get(b"Font").ok() else { continue };
        let Some(dict) = font::resolve_dict(doc, font_obj) else { continue };
        for (name, object) in dict.iter() {
            into.entry(name.clone()).or_insert_with(|| font::load_font(doc, object));
        }
    }
}

fn lookup<'a>(doc: &'a PdfFile, resources: &[&'a Dictionary], kind: &[u8], name: &[u8]) -> Option<&'a Object> {
    for level in resources {
        let Some(obj) = level.get(kind).ok() else { continue };
        let Some(dict) = font::resolve_dict(doc, obj) else { continue };
        if let Ok(found) = dict.get(name) {
            return Some(found);
        }
    }
    None
}

fn replace_fonts(doc: &PdfFile, resources: &Dictionary, into: &mut HashMap<Vec<u8>, FontInfo>) {
    let Some(font_obj) = resources.get(b"Font").ok() else { return };
    let Some(dict) = font::resolve_dict(doc, font_obj) else { return };
    for (name, object) in dict.iter() {
        into.insert(name.clone(), font::load_font(doc, object));
    }
}

fn alt_color(args: &[Object], current: Color) -> Color {
    let nums: Vec<f32> = args.iter().filter_map(|object| match object {
        Object::Integer(v) => Some(*v as f32),
        Object::Real(v) => Some(*v),
        _ => None,
    }).collect();
    match nums.as_slice() {
        [gray] => Color { r: *gray, g: *gray, b: *gray, a: current.a },
        [r, g, b] => Color { r: *r, g: *g, b: *b, a: current.a },
        [c, m, y, k] => Color { r: (1.0 - c) * (1.0 - k), g: (1.0 - m) * (1.0 - k), b: (1.0 - y) * (1.0 - k), a: current.a },
        _ => current,
    }
}

impl State {
    fn new() -> Self {
        Self {
            ctm: Matrix::identity(),
            fill: Color { r: 0.0, g: 0.0, b: 0.0, a: 1.0 },
            stroke: Color { r: 0.0, g: 0.0, b: 0.0, a: 1.0 },
            line_width: 1.0,
            char_spacing: 0.0,
            word_spacing: 0.0,
            horiz: 100.0,
            leading: 0.0,
            font_key: Vec::new(),
            font_size: 12.0,
            render_mode: 0,
            rise: 0.0,
            text: Matrix::identity(),
            line: Matrix::identity(),
        }
    }

    fn move_text(&mut self, x: f32, y: f32, set_leading: bool) -> Result<(), String> {
        if set_leading { self.leading = -y; }
        self.line = Matrix::concat(Matrix::translate(x, y), self.line);
        self.text = self.line;
        Ok(())
    }
}

impl Path {
    fn new() -> Self { Self { segments: Vec::new(), current: Point { x: 0.0, y: 0.0 }, start: Point { x: 0.0, y: 0.0 } } }
    fn move_to(&mut self, ctm: Matrix, x: f32, y: f32) {
        let (x, y) = ctm.transform(x, y);
        self.current = Point { x, y };
        self.start = self.current;
        self.segments.push(PathSegment::Move(self.current));
    }
    fn line_to(&mut self, ctm: Matrix, x: f32, y: f32) {
        let (x, y) = ctm.transform(x, y);
        self.current = Point { x, y };
        self.segments.push(PathSegment::Line(self.current));
    }
    fn curve(&mut self, ctm: Matrix, args: &[Object]) -> Result<(), String> {
        let (x1, y1) = ctm.transform(num_at(args, 0)?, num_at(args, 1)?);
        let (x2, y2) = ctm.transform(num_at(args, 2)?, num_at(args, 3)?);
        let (x3, y3) = ctm.transform(num_at(args, 4)?, num_at(args, 5)?);
        self.current = Point { x: x3, y: y3 };
        self.segments.push(PathSegment::Curve { c1: Point { x: x1, y: y1 }, c2: Point { x: x2, y: y2 }, end: self.current });
        Ok(())
    }
    fn curve_v(&mut self, ctm: Matrix, args: &[Object]) -> Result<(), String> {
        let (x2, y2) = ctm.transform(num_at(args, 0)?, num_at(args, 1)?);
        let (x3, y3) = ctm.transform(num_at(args, 2)?, num_at(args, 3)?);
        self.segments.push(PathSegment::Curve { c1: self.current, c2: Point { x: x2, y: y2 }, end: Point { x: x3, y: y3 } });
        self.current = Point { x: x3, y: y3 };
        Ok(())
    }
    fn curve_y(&mut self, ctm: Matrix, args: &[Object]) -> Result<(), String> {
        let (x1, y1) = ctm.transform(num_at(args, 0)?, num_at(args, 1)?);
        let (x3, y3) = ctm.transform(num_at(args, 2)?, num_at(args, 3)?);
        let end = Point { x: x3, y: y3 };
        self.segments.push(PathSegment::Curve { c1: Point { x: x1, y: y1 }, c2: end, end });
        self.current = end;
        Ok(())
    }
    fn rect(&mut self, ctm: Matrix, args: &[Object]) -> Result<(), String> {
        let x = num_at(args, 0)?;
        let y = num_at(args, 1)?;
        let w = num_at(args, 2)?;
        let h = num_at(args, 3)?;
        self.move_to(ctm, x, y);
        self.line_to(ctm, x + w, y);
        self.line_to(ctm, x + w, y + h);
        self.line_to(ctm, x, y + h);
        self.close();
        Ok(())
    }
    fn close(&mut self) {
        self.segments.push(PathSegment::Close);
        self.current = self.start;
    }
    fn clear(&mut self) { self.segments.clear(); }
    fn paint(&mut self, state: &State, name: &str) -> PathShape {
        let fill = matches!(name, "f" | "F" | "f*" | "B" | "B*" | "b" | "b*");
        let stroke = matches!(name, "S" | "s" | "B" | "B*" | "b" | "b*");
        let points = points_of(&self.segments);
        PathShape {
            bounds: bounds_of(&points),
            stroke_width: state.line_width * state.ctm.scale_x(),
            stroke: stroke.then_some(state.stroke),
            fill: fill.then_some(state.fill),
            even_odd: matches!(name, "f*" | "B*" | "b*"),
            segments: std::mem::take(&mut self.segments),
        }
    }
}

fn points_of(segments: &[PathSegment]) -> Vec<(f32, f32)> {
    let mut points = Vec::new();
    for segment in segments {
        match segment {
            PathSegment::Move(p) | PathSegment::Line(p) => points.push((p.x, p.y)),
            PathSegment::Curve { c1, c2, end } => points.extend([(c1.x, c1.y), (c2.x, c2.y), (end.x, end.y)]),
            PathSegment::Close => {}
        }
    }
    points
}

fn bounds_of(points: &[(f32, f32)]) -> Rect {
    let Some((first, rest)) = points.split_first() else { return Rect { x: 0.0, y: 0.0, width: 0.0, height: 0.0 } };
    let (mut min_x, mut min_y, mut max_x, mut max_y) = (first.0, first.1, first.0, first.1);
    for (x, y) in rest {
        min_x = min_x.min(*x); min_y = min_y.min(*y); max_x = max_x.max(*x); max_y = max_y.max(*y);
    }
    Rect::from_minmax(min_x, min_y, max_x, max_y)
}

fn matrix_from(args: &[Object]) -> Result<Matrix, String> {
    Ok(Matrix { a: num_at(args, 0)?, b: num_at(args, 1)?, c: num_at(args, 2)?, d: num_at(args, 3)?, e: num_at(args, 4)?, f: num_at(args, 5)? })
}

fn num_at(args: &[Object], index: usize) -> Result<f32, String> {
    args.get(index).map(num).ok_or_else(|| format!("missing operand {index}"))
}

fn num(object: &Object) -> f32 {
    match object { Object::Integer(v) => *v as f32, Object::Real(v) => *v, _ => 0.0 }
}

fn gray(value: f32, alpha: f32) -> Color { Color { r: value, g: value, b: value, a: alpha } }

fn rgb(args: &[Object], alpha: f32) -> Result<Color, String> {
    Ok(Color { r: num_at(args, 0)?, g: num_at(args, 1)?, b: num_at(args, 2)?, a: alpha })
}

fn cmyk(args: &[Object], alpha: f32) -> Result<Color, String> {
    let (c, m, y, k) = (num_at(args, 0)?, num_at(args, 1)?, num_at(args, 2)?, num_at(args, 3)?);
    Ok(Color { r: (1.0 - c) * (1.0 - k), g: (1.0 - m) * (1.0 - k), b: (1.0 - y) * (1.0 - k), a: alpha })
}

fn filter_name(dict: &Dictionary) -> String {
    match dict.get(b"Filter") {
        Ok(Object::Name(name)) => String::from_utf8_lossy(name).into_owned(),
        Ok(Object::Array(items)) => items.iter().filter_map(|o| o.as_name().ok()).map(|n| String::from_utf8_lossy(n).into_owned()).collect::<Vec<_>>().join(" "),
        _ => String::new(),
    }
}

fn color_name(dict: &Dictionary) -> String {
    match dict.get(b"ColorSpace") {
        Ok(Object::Name(name)) => String::from_utf8_lossy(name).into_owned(),
        Ok(Object::Array(items)) => items.first().and_then(|o| o.as_name().ok()).map(|n| String::from_utf8_lossy(n).into_owned()).unwrap_or_default(),
        _ => String::new(),
    }
}

