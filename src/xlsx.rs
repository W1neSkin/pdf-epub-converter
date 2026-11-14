//! Таблица в файле Excel. Пишется только по запросу, не вместе с HTML страницы.

use rust_xlsxwriter::Workbook;

use crate::csv::cell_text;
use crate::Table;

/// Книга Excel из одной таблицы: строка листа — строка таблицы, ячейка — её текст.
pub fn table_to_xlsx(table: &Table) -> Result<Vec<u8>, String> {
    let mut workbook = Workbook::new();
    let sheet = workbook.add_worksheet();
    for (row_index, row) in table.rows.iter().enumerate() {
        for (col_index, cell) in row.cells.iter().enumerate() {
            let column = u16::try_from(col_index).map_err(|_| "too many columns".to_string())?;
            sheet
                .write_string(row_index as u32, column, &cell_text(&cell.content))
                .map_err(|err| err.to_string())?;
        }
    }
    for (index, column) in table.columns.iter().enumerate() {
        let width = (f64::from(column.width) / 7.0).clamp(8.0, 60.0);
        let column = u16::try_from(index).map_err(|_| "too many columns".to_string())?;
        sheet.set_column_width(column, width).map_err(|err| err.to_string())?;
    }
    workbook.save_to_buffer().map_err(|err| err.to_string())
}
