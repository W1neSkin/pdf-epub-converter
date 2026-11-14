//! Сборка глифов в строки и абзацы и поиск таблиц по сетке линий.
//! Колонки таблицы здесь уже имеют ширину: писателю HTML не нужно угадывать её заново.

use crate::geom::{Point, Rect};
use crate::model::{Column, Element, Font, Glyph, PathSegment, Row, Table, TextBlock, TextLine, TextSource, TextSpan};

use super::exec::{GlyphPaint, Paint};

pub fn group(paints: Vec<Paint>) -> Vec<Element> {
    let mut glyphs = Vec::new();
    let mut elements = Vec::new();
    for paint in paints {
        match paint {
            Paint::Glyph(glyph) => glyphs.push(glyph),
            other => {
                elements.extend(blocks_from(&glyphs));
                glyphs.clear();
                push_other(&mut elements, other);
            }
        }
    }
    elements.extend(blocks_from(&glyphs));
    lift_tables(elements)
}

fn push_other(elements: &mut Vec<Element>, paint: Paint) {
    match paint {
        Paint::Image(image) => elements.push(Element::Image(image)),
        Paint::Path(path) => elements.push(Element::Path(path)),
        Paint::Glyph(_) => {}
    }
}

fn blocks_from(glyphs: &[GlyphPaint]) -> Vec<Element> {
    let mut blocks: Vec<Vec<Vec<&GlyphPaint>>> = Vec::new();
    for glyph in glyphs {
        if glyph.text.is_empty() {
            continue;
        }
        let Some(block) = blocks.last_mut() else {
            blocks.push(vec![vec![glyph]]);
            continue;
        };
        let line = block.last().unwrap();
        let prev = line.last().unwrap();
        if same_line(prev, glyph) {
            block.last_mut().unwrap().push(glyph);
        } else if same_block(block, glyph) {
            block.push(vec![glyph]);
        } else {
            blocks.push(vec![vec![glyph]]);
        }
    }
    blocks.into_iter().map(block_element).collect()
}

fn same_line(prev: &GlyphPaint, next: &GlyphPaint) -> bool {
    let size = prev.size.max(1.0);
    (prev.origin.y - next.origin.y).abs() < size * 0.35 && next.origin.x + 1.0 >= prev.origin.x
}

fn same_block(block: &[Vec<&GlyphPaint>], next: &GlyphPaint) -> bool {
    let first = block[0][0];
    let size = first.size.max(1.0);
    let previous_y = block.last().unwrap()[0].origin.y;
    let gap = previous_y - next.origin.y;
    gap > size * 0.3 && gap < size * 2.2 && (next.origin.x - first.origin.x).abs() < size * 4.0
}

fn block_element(lines: Vec<Vec<&GlyphPaint>>) -> Element {
    // Видимость берётся из режима рисования текста. Режим 3 в PDF текст не рисует.
    let visible = lines.iter().flatten().all(|glyph| glyph.visible);
    let text_lines: Vec<TextLine> = lines.into_iter().map(line_element).collect();
    let bounds = text_lines.iter().map(|line| line.bounds).reduce(Rect::union).unwrap_or(Rect { x: 0.0, y: 0.0, width: 0.0, height: 0.0 });
    Element::Text(TextBlock { bounds, source: TextSource::Page, visible, lines: text_lines })
}

fn line_element(glyphs: Vec<&GlyphPaint>) -> TextLine {
    let mut spans = Vec::new();
    for glyph in glyphs {
        let same = spans.last().is_some_and(|span: &TextSpan| {
            span.font.size == glyph.size && span.font.bold == glyph.bold && span.font.italic == glyph.italic && span.color == glyph.color && span.font.name == glyph.font_name
        });
        if !same {
            spans.push(TextSpan {
                bounds: glyph_bounds(glyph),
                text: String::new(),
                font: Font { name: glyph.font_name.clone(), size: glyph.size, bold: glyph.bold, italic: glyph.italic },
                color: glyph.color,
                glyphs: Vec::new(),
            });
        }
        let span = spans.last_mut().unwrap();
        span.text.push_str(&glyph.text);
        span.glyphs.push(model_glyph(glyph));
        span.bounds = span.bounds.union(glyph_bounds(glyph));
    }
    let bounds = spans.iter().map(|span| span.bounds).reduce(Rect::union).unwrap();
    TextLine { bounds, spans }
}

fn model_glyph(glyph: &GlyphPaint) -> Glyph {
    Glyph {
        bounds: glyph_bounds(glyph),
        origin: glyph.origin,
        rotation: glyph.rotation,
        ch: glyph.text.chars().next(),
        glyph_id: None,
    }
}

fn glyph_bounds(glyph: &GlyphPaint) -> Rect {
    let width = if glyph.advance.abs() > 0.01 { glyph.advance.abs() } else { glyph.size * 0.5 };
    Rect { x: glyph.origin.x, y: glyph.origin.y - glyph.size * 0.2, width, height: glyph.size }
}

/// Строки, которые лежат в одной сетке линий, становятся ячейками таблицы.
/// Линии с разными левым и правым краем — это разные рамки, не одна огромная таблица.
fn lift_tables(elements: Vec<Element>) -> Vec<Element> {
    // Сначала рамка из линий. Текст, который в неё попал, второму поиску уже не виден.
    // Потом слова без рамки: колонки там заданы зазорами, а не линиями.
    let ruled = lift_ruled_tables(elements);
    super::table_words::add_word_tables(ruled)
}

fn lift_ruled_tables(elements: Vec<Element>) -> Vec<Element> {
    let lines = line_segments(&elements);
    let tables = find_tables(&lines, &elements);
    if tables.is_empty() {
        return elements;
    }
    let mut kept = Vec::new();
    let mut placed = vec![false; tables.len()];
    for element in elements {
        if let Some(index) = tables.iter().position(|table| inside_table(table, &element)) {
            if !placed[index] {
                kept.push(Element::Table(tables[index].clone()));
                placed[index] = true;
            }
            continue;
        }
        kept.push(element);
    }
    for (index, table) in tables.into_iter().enumerate() {
        if !placed[index] {
            kept.push(Element::Table(table));
        }
    }
    kept
}

fn inside_table(table: &Table, element: &Element) -> bool {
    let bounds = match element {
        Element::Text(text) => text.bounds,
        Element::Path(path) => path.bounds,
        _ => return false,
    };
    let cx = bounds.x + bounds.width / 2.0;
    let cy = bounds.y + bounds.height / 2.0;
    table.bounds.contains(cx, cy)
}

struct Seg { x0: f32, y0: f32, x1: f32, y1: f32 }

fn line_segments(elements: &[Element]) -> Vec<Seg> {
    let mut lines = Vec::new();
    for element in elements {
        let Element::Path(path) = element else { continue };
        let mut cursor = Point { x: 0.0, y: 0.0 };
        let mut start = cursor;
        for segment in &path.segments {
            match segment {
                PathSegment::Move(p) => { cursor = *p; start = *p; }
                PathSegment::Line(p) => {
                    lines.push(Seg { x0: cursor.x, y0: cursor.y, x1: p.x, y1: p.y });
                    cursor = *p;
                }
                PathSegment::Close => {
                    lines.push(Seg { x0: cursor.x, y0: cursor.y, x1: start.x, y1: start.y });
                    cursor = start;
                }
                PathSegment::Curve { end, .. } => cursor = *end,
            }
        }
    }
    lines
}

fn find_tables(lines: &[Seg], elements: &[Element]) -> Vec<Table> {
    let horizontal: Vec<&Seg> = lines.iter().filter(|seg| (seg.y0 - seg.y1).abs() < 1.0 && (seg.x0 - seg.x1).abs() > 20.0).collect();
    let vertical: Vec<&Seg> = lines.iter().filter(|seg| (seg.x0 - seg.x1).abs() < 1.0 && (seg.y0 - seg.y1).abs() > 8.0).collect();
    let mut used = vec![false; horizontal.len()];
    let mut tables = Vec::new();
    for start in 0..horizontal.len() {
        if used[start] {
            continue;
        }
        let (left, right) = ends(horizontal[start]);
        let mut group = vec![horizontal[start]];
        used[start] = true;
        for (index, seg) in horizontal.iter().enumerate().skip(start + 1) {
            let (x0, x1) = ends(seg);
            if (x0 - left).abs() < 4.0 && (x1 - right).abs() < 4.0 {
                group.push(seg);
                used[index] = true;
            }
        }
        if let Some(table) = table_from_group(&group, &vertical, elements) {
            tables.push(table);
        }
    }
    tables
}

fn table_from_group(group: &[&Seg], vertical: &[&Seg], elements: &[Element]) -> Option<Table> {
    if group.len() < 3 {
        return None;
    }
    let (left, right) = ends(group[0]);
    let mut ys: Vec<f32> = group.iter().map(|seg| (seg.y0 + seg.y1) / 2.0).collect();
    ys.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    ys.dedup_by(|a, b| (*a - *b).abs() < 1.5);
    if ys.len() < 3 {
        return None;
    }
    let top = ys[0];
    let bottom = ys[ys.len() - 1];
    let mut xs: Vec<f32> = vertical
        .iter()
        .map(|seg| ((seg.x0 + seg.x1) / 2.0, seg.y0.min(seg.y1), seg.y0.max(seg.y1)))
        .filter(|(x, y0, y1)| *x >= left - 2.0 && *x <= right + 2.0 && *y1 >= top - 2.0 && *y0 <= bottom + 2.0)
        .map(|(x, _, _)| x)
        .collect();
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    xs.dedup_by(|a, b| (*a - *b).abs() < 1.5);
    if xs.len() < 2 {
        return None;
    }
    let bounds = Rect::from_minmax(xs[0], bottom, xs[xs.len() - 1], top);
    let columns: Vec<Column> = xs.windows(2).map(|pair| Column { width: pair[1] - pair[0] }).collect();
    let mut rows = Vec::new();
    for pair in ys.windows(2) {
        let (row_top, row_bottom) = (pair[0], pair[1]);
        let mut cells = Vec::new();
        for col in xs.windows(2) {
            let cell_bounds = Rect { x: col[0], y: row_bottom, width: col[1] - col[0], height: row_top - row_bottom };
            let content = elements.iter().filter_map(|element| {
                let Element::Text(text) = element else { return None };
                let cx = text.bounds.x + text.bounds.width / 2.0;
                let cy = text.bounds.y + text.bounds.height / 2.0;
                cell_bounds.contains(cx, cy).then(|| Element::Text(text.clone()))
            }).collect();
            cells.push(crate::Cell { bounds: cell_bounds, col_span: 1, row_span: 1, content });
        }
        rows.push(Row { height: row_top - row_bottom, cells });
    }
    let filled = rows.iter().flat_map(|row| &row.cells).filter(|cell| !cell.content.is_empty()).count();
    if filled < 2 {
        return None;
    }
    Some(Table { bounds, columns, rows, ruled: true })
}

fn ends(seg: &Seg) -> (f32, f32) {
    if seg.x0 <= seg.x1 { (seg.x0, seg.x1) } else { (seg.x1, seg.x0) }
}

