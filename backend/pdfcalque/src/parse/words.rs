//! Слова и строки страницы для поиска таблицы без рамки.
//!
//! Пробел в PDF часто не нарисован отдельной буквой: он виден как щель между глифами.
//! Маленькая щель делит слова. Широкая щель — это уже промежуток между колонками.

use crate::geom::{Color, Rect};
use crate::model::{Element, Font, Glyph, TextSpan};

#[derive(Clone)]
pub(super) struct Word {
    pub text: String,
    pub glyphs: Vec<Glyph>,
    pub font: Font,
    pub color: Color,
    pub bounds: Rect,
    pub baseline: f32,
}

pub(super) struct CellWords {
    pub words: Vec<Word>,
    pub bounds: Rect,
}

pub(super) struct Line {
    pub cells: Vec<CellWords>,
    pub baseline: f32,
    pub size: f32,
}

pub(super) fn page_lines(elements: &[Element]) -> Vec<Line> {
    lines_of(words_of(elements))
}

fn words_of(elements: &[Element]) -> Vec<Word> {
    let mut words = Vec::new();
    for element in elements {
        let Element::Text(block) = element else { continue };
        // Невидимый слой распознавания на лист не попадает, в таблицу его тоже не берём.
        if !block.visible {
            continue;
        }
        for line in &block.lines {
            for span in &line.spans {
                push_span_words(&mut words, span);
            }
        }
    }
    words
}

fn push_span_words(words: &mut Vec<Word>, span: &TextSpan) {
    let mut current: Option<Word> = None;
    let size = span.font.size.max(1.0);
    for glyph in &span.glyphs {
        // Повёрнутая буква не лежит в обычной строке таблицы.
        if glyph.rotation.abs() > 0.5 {
            continue;
        }
        let Some(ch) = glyph.ch else { continue };
        let broken = current.as_ref().is_some_and(|word| {
            let right = word.bounds.x + word.bounds.width;
            glyph.bounds.x - right > size * 0.2 || (word.baseline - glyph.origin.y).abs() > size * 0.35
        });
        if broken {
            if let Some(word) = current.take() {
                words.push(word);
            }
        }
        let word = current.get_or_insert_with(|| Word {
            text: String::new(),
            glyphs: Vec::new(),
            font: span.font.clone(),
            color: span.color,
            bounds: glyph.bounds,
            baseline: glyph.origin.y,
        });
        word.text.push(ch);
        word.glyphs.push(glyph.clone());
        word.bounds = word.bounds.union(glyph.bounds);
    }
    if let Some(word) = current {
        words.push(word);
    }
}

fn lines_of(mut words: Vec<Word>) -> Vec<Line> {
    // Большая y в PDF — верх страницы, поэтому строки идут сверху вниз.
    words.sort_by(|a, b| b.baseline.total_cmp(&a.baseline).then(a.bounds.x.total_cmp(&b.bounds.x)));
    let mut rows: Vec<Vec<Word>> = Vec::new();
    for word in words {
        let size = word.font.size.max(1.0);
        let same = rows.last().is_some_and(|row| (row[0].baseline - word.baseline).abs() < size * 0.4);
        if same {
            rows.last_mut().unwrap().push(word);
        } else {
            rows.push(vec![word]);
        }
    }
    rows.into_iter().map(line_from_row).collect()
}

fn line_from_row(mut row: Vec<Word>) -> Line {
    row.sort_by(|a, b| a.bounds.x.total_cmp(&b.bounds.x));
    let size = row.iter().map(|word| word.font.size).fold(1.0, f32::max);
    let mut cells: Vec<CellWords> = Vec::new();
    for word in row {
        let gap = cells.last().map(|cell| word.bounds.x - (cell.bounds.x + cell.bounds.width)).unwrap_or(0.0);
        if cells.is_empty() || gap >= column_gap(size) {
            cells.push(CellWords { bounds: word.bounds, words: vec![word] });
        } else {
            let cell = cells.last_mut().unwrap();
            cell.bounds = cell.bounds.union(word.bounds);
            cell.words.push(word);
        }
    }
    let baseline = cells.first().map(|cell| cell.words[0].baseline).unwrap_or(0.0);
    Line { cells, baseline, size }
}

/// Щель колонки шире обычного пробела. Иначе предложение разъедется по клеткам.
fn column_gap(size: f32) -> f32 {
    (size * 1.8).max(14.0)
}

/// Строки, чьи клетки не перелезают через общий зазор между колонками.
/// Заголовок, склеенный из двух колонок, так отпадает. Остаются ровные ряды.
pub(super) fn consistent_rows(lines: &[Line]) -> Option<&[Line]> {
    let cols = lines.first()?.cells.len();
    if cols < 2 {
        return None;
    }
    let mut cuts = Vec::new();
    for col in 0..cols - 1 {
        let mut mids: Vec<f32> = lines
            .iter()
            .filter(|line| line.cells.len() == cols)
            .map(|line| {
                let left = &line.cells[col];
                let right = &line.cells[col + 1];
                (left.bounds.x + left.bounds.width + right.bounds.x) / 2.0
            })
            .collect();
        mids.sort_by(|a, b| a.total_cmp(b));
        cuts.push(mids[mids.len() / 2]);
    }
    let fits = |line: &Line| {
        line.cells.len() == cols
            && line.cells.iter().all(|cell| {
                let x0 = cell.bounds.x + 2.0;
                let x1 = cell.bounds.x + cell.bounds.width - 2.0;
                cuts.iter().all(|cut| *cut <= x0 || *cut >= x1)
            })
    };
    let mut best: Option<(usize, usize)> = None;
    let mut start = 0;
    for index in 0..=lines.len() {
        let open = index < lines.len() && fits(&lines[index]);
        if open {
            continue;
        }
        if index - start >= 3 && best.map(|(from, to)| to - from < index - start).unwrap_or(true) {
            best = Some((start, index));
        }
        start = index + 1;
    }
    let (from, to) = best?;
    Some(&lines[from..to])
}
