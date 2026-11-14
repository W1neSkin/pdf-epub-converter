//! Таблица без нарисованной рамки.
//!
//! Берём строки из слов. Несколько коротких строк с одним и тем же числом колонок — таблица.
//! Длинный текст в две колонки не берём: это абзацы книги, а не клетки.
//! Клетки такой таблицы на странице не обводятся: линий в PDF не было.

use crate::geom::Rect;
use crate::model::{Column, Element, Row, Table, TextBlock, TextLine, TextSource, TextSpan};

use super::words::{self, Line, Word};

/// Текст, который не попал в сетку линий, может сложиться в таблицу по колонкам слов.
pub fn add_word_tables(elements: Vec<Element>) -> Vec<Element> {
    let tables = find_tables(&elements);
    if tables.is_empty() {
        return elements;
    }
    let mut kept = Vec::new();
    let mut placed = vec![false; tables.len()];
    for element in elements {
        let Element::Text(block) = element else {
            kept.push(element);
            continue;
        };
        // Середина строки внутри таблицы — буквы уже в клетке, на странице их не оставляем.
        let source = block.source;
        let visible = block.visible;
        let mut left = Vec::new();
        for line in block.lines {
            let cx = line.bounds.x + line.bounds.width / 2.0;
            let cy = line.bounds.y + line.bounds.height / 2.0;
            if let Some(index) = tables.iter().position(|table| table.bounds.contains(cx, cy)) {
                if !placed[index] {
                    kept.push(Element::Table(tables[index].clone()));
                    placed[index] = true;
                }
            } else {
                left.push(line);
            }
        }
        if let Some(text) = text_from_lines(source, visible, left) {
            kept.push(Element::Text(text));
        }
    }
    for (index, table) in tables.into_iter().enumerate() {
        if !placed[index] {
            kept.push(Element::Table(table));
        }
    }
    kept
}

fn find_tables(elements: &[Element]) -> Vec<Table> {
    let lines = words::page_lines(elements);
    let mut tables = Vec::new();
    let mut index = 0;
    while index < lines.len() {
        if let Some(end) = band_end(&lines, index) {
            if let Some(table) = table_from(&lines[index..end]) {
                tables.push(table);
                index = end;
                continue;
            }
        }
        index += 1;
    }
    tables
}

fn band_end(lines: &[Line], start: usize) -> Option<usize> {
    if lines[start].cells.len() < 2 {
        return None;
    }
    let mut end = start + 1;
    while end < lines.len() && continues(&lines[end - 1], &lines[end]) {
        end += 1;
    }
    (end - start >= 3).then_some(end)
}

fn continues(prev: &Line, next: &Line) -> bool {
    let size = prev.size.max(next.size).max(1.0);
    let gap = prev.baseline - next.baseline;
    // Соседние строки таблицы близко. Большой разрыв — это уже другой абзац.
    gap > size * 0.45 && gap < size * 3.2 && aligned(prev, next)
}

fn aligned(prev: &Line, next: &Line) -> bool {
    if prev.cells.len() != next.cells.len() {
        return false;
    }
    prev.cells.iter().zip(&next.cells).all(|(left, right)| {
        let left_mid = left.bounds.x + left.bounds.width / 2.0;
        let right_mid = right.bounds.x + right.bounds.width / 2.0;
        let left_end = left.bounds.x + left.bounds.width;
        let right_end = right.bounds.x + right.bounds.width;
        // Левый край, правый или середина: число в колонке бывает прижато вправо.
        (left.bounds.x - right.bounds.x).abs() < 14.0
            || (left_end - right_end).abs() < 14.0
            || (left_mid - right_mid).abs() < 14.0
    })
}

fn table_from(lines: &[Line]) -> Option<Table> {
    // Сначала выкидываем строку, которая наехала на две колонки сразу. Часто это кривой заголовок.
    let lines = words::consistent_rows(lines)?;
    if !cells_are_short(lines) {
        return None;
    }
    let count = lines[0].cells.len();
    let mut xs: Vec<f32> = (0..count)
        .map(|col| lines.iter().map(|line| line.cells[col].bounds.x).fold(f32::MAX, f32::min))
        .collect();
    let right = lines
        .iter()
        .map(|line| {
            let cell = line.cells.last().unwrap();
            cell.bounds.x + cell.bounds.width
        })
        .fold(0.0, f32::max);
    xs.push(right);
    if xs.windows(2).any(|pair| pair[1] < pair[0] + 4.0) {
        return None;
    }
    let size = lines.iter().map(|line| line.size).fold(1.0, f32::max);
    let top = lines[0].baseline + size * 0.9;
    let bottom = lines[lines.len() - 1].baseline - size * 0.35;
    let bounds = Rect::from_minmax(xs[0], bottom, *xs.last().unwrap(), top);
    let columns = xs.windows(2).map(|pair| Column { width: pair[1] - pair[0] }).collect();
    let mut rows = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        let row_top = if index == 0 { top } else { (lines[index - 1].baseline + line.baseline) / 2.0 };
        let row_bottom = if index + 1 == lines.len() { bottom } else { (line.baseline + lines[index + 1].baseline) / 2.0 };
        let mut cells = Vec::new();
        for (col, cell) in line.cells.iter().enumerate() {
            cells.push(crate::Cell {
                bounds: Rect::from_minmax(xs[col], row_bottom, xs[col + 1], row_top),
                col_span: 1,
                row_span: 1,
                content: vec![block_from_words(&cell.words)],
            });
        }
        rows.push(Row { height: row_top - row_bottom, cells });
    }
    Some(Table { bounds, columns, rows, ruled: false })
}

/// Короткий текст в клетке. Медиана длиннее 28 букв — это строка книги, не таблица.
fn cells_are_short(lines: &[Line]) -> bool {
    let mut lengths = Vec::new();
    for line in lines {
        for cell in &line.cells {
            let chars: usize = cell.words.iter().map(|word| word.text.chars().count()).sum();
            lengths.push(chars + cell.words.len().saturating_sub(1));
        }
    }
    if lengths.len() < 6 {
        return false;
    }
    lengths.sort_unstable();
    let median = lengths[lengths.len() / 2];
    let long = lengths.iter().filter(|len| **len > 40).count();
    median <= 28 && long * 2 <= lengths.len()
}

fn block_from_words(words: &[Word]) -> Element {
    let bounds = words.iter().map(|word| word.bounds).reduce(Rect::union).unwrap();
    let mut spans: Vec<TextSpan> = Vec::new();
    for word in words {
        let same = spans.last().is_some_and(|span| {
            span.font.name == word.font.name
                && span.font.size == word.font.size
                && span.font.bold == word.font.bold
                && span.font.italic == word.font.italic
                && span.color == word.color
        });
        if !same {
            spans.push(TextSpan {
                bounds: word.bounds,
                text: String::new(),
                font: word.font.clone(),
                color: word.color,
                glyphs: Vec::new(),
            });
        }
        let span = spans.last_mut().unwrap();
        if !span.text.is_empty() {
            span.text.push(' ');
        }
        span.text.push_str(&word.text);
        span.glyphs.extend(word.glyphs.iter().cloned());
        span.bounds = span.bounds.union(word.bounds);
    }
    Element::Text(TextBlock {
        bounds,
        source: TextSource::Page,
        visible: true,
        lines: vec![TextLine { bounds, spans }],
    })
}

fn text_from_lines(source: TextSource, visible: bool, lines: Vec<TextLine>) -> Option<TextBlock> {
    if lines.is_empty() {
        return None;
    }
    let bounds = lines.iter().map(|line| line.bounds).reduce(Rect::union).unwrap();
    Some(TextBlock { bounds, source, visible, lines })
}
