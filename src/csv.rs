//! Таблица в CSV. Вызывается только когда этот файл нужен, не при каждой конвертации.

use crate::{Element, Table};

/// Ячейки по строкам. Текст ячейки — буквы её элементов. Запятая и кавычки экранируются.
pub fn table_to_csv(table: &Table) -> String {
    let mut out = String::new();
    for row in &table.rows {
        for (index, cell) in row.cells.iter().enumerate() {
            if index > 0 {
                out.push(',');
            }
            out.push_str(&csv_cell(&cell_text(&cell.content)));
        }
        out.push('\n');
    }
    out
}

pub(crate) fn cell_text(elements: &[Element]) -> String {
    let mut text = String::new();
    for element in elements {
        match element {
            Element::Text(block) => {
                for line in &block.lines {
                    // Пробел между кусками строки только если между ними щель.
                    // Смена шрифта внутри слова пробелом не является.
                    let mut previous: Option<(f32, f32)> = None;
                    for span in &line.spans {
                        if let Some((right, size)) = previous {
                            let gap = span.bounds.x - right;
                            if gap > size * 0.15 && !text.ends_with(' ') {
                                text.push(' ');
                            }
                        } else if !text.is_empty() && !text.ends_with(' ') {
                            text.push(' ');
                        }
                        text.push_str(&span.text);
                        previous = Some((span.bounds.x + span.bounds.width, span.font.size.max(1.0)));
                    }
                }
            }
            Element::Table(inner) => {
                for row in &inner.rows {
                    for cell in &row.cells {
                        let nested = cell_text(&cell.content);
                        if !nested.is_empty() {
                            if !text.is_empty() && !text.ends_with(' ') {
                                text.push(' ');
                            }
                            text.push_str(&nested);
                        }
                    }
                }
            }
            _ => {}
        }
    }
    text
}

fn csv_cell(text: &str) -> String {
    if text.contains([',', '"', '\n']) {
        format!("\"{}\"", text.replace('"', "\"\""))
    } else {
        text.to_string()
    }
}
