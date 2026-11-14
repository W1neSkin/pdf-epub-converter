//! Результат разбора PDF.
//!
//! Парсер заполняет эти структуры и больше ничего не решает про HTML.
//! Любой выходной формат потом только читает их: элементы, порядок, положение и атрибуты.
//!
//! Порядок элемента — его место в списке. Внутри таблицы порядок задают строки и ячейки.

use crate::geom::{Color, Point, Rect};

/// Разобранный документ.
#[derive(Clone, Debug)]
pub struct Document {
    pub pages: Vec<Page>,
    /// Название из свойств PDF. Пустая строка — в EPUB будет «Книга».
    pub title: String,
    /// Язык из каталога PDF, например `ru` или `en`. Пустая строка — в EPUB будет `ru`.
    pub language: String,
    /// Оглавление PDF, если в файле есть закладки. Пустое — в книге останутся номера страниц.
    pub outline: Vec<Heading>,
    /// Шрифты книги. В EPUB это файлы в папке `fonts`, страница ссылается на них по имени.
    pub faces: Vec<Face>,
}

/// Файл шрифта, который можно вложить в EPUB. `data` — OpenType или TrueType.
#[derive(Clone, Debug)]
pub struct Face {
    pub family: String,
    pub bold: bool,
    pub italic: bool,
    pub data: Vec<u8>,
}

/// Пункт оглавления. `page` — номер страницы с нуля.
/// `y` — расстояние от верхнего края листа до места, куда ведёт закладка.
/// `None` значит «начало страницы». Дети — вложенные разделы.
#[derive(Clone, Debug)]
pub struct Heading {
    pub title: String,
    pub page: usize,
    pub y: Option<f32>,
    pub children: Vec<Heading>,
}

/// Одна страница.
#[derive(Clone, Debug)]
pub struct Page {
    /// Ширина видимой области в пунктах.
    pub width: f32,
    /// Высота видимой области в пунктах.
    pub height: f32,
    /// Элементы страницы по порядку.
    pub elements: Vec<Element>,
}

/// Элемент, который можно перенести в другой формат.
#[derive(Clone, Debug)]
pub enum Element {
    Text(TextBlock),
    Image(Image),
    Path(PathShape),
    Table(Table),
}

/// Абзац или отдельная группа строк.
#[derive(Clone, Debug)]
pub struct TextBlock {
    pub bounds: Rect,
    /// Откуда взялись буквы.
    pub source: TextSource,
    /// false, если PDF рисует этот текст невидимым (так бывает у слоя распознавания в скане).
    pub visible: bool,
    pub lines: Vec<TextLine>,
}

/// Откуда взялся текст.
///
/// `Page` — обычный PDF: буквы прочитаны из самого файла.
/// `Ocr` — только скан, в файле была картинка и не было текста.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TextSource {
    /// Команды, шрифт и координаты из файла PDF.
    Page,
    /// Буквы распознаны с картинки скана.
    Ocr,
}

#[derive(Clone, Debug)]
pub struct TextLine {
    pub bounds: Rect,
    pub spans: Vec<TextSpan>,
}

/// Кусок строки с одним шрифтом и одним цветом.
#[derive(Clone, Debug)]
pub struct TextSpan {
    pub bounds: Rect,
    pub text: String,
    pub font: Font,
    pub color: Color,
    /// Глифы по порядку. У текста из OCR здесь одна запись на символ, без кода глифа из шрифта.
    pub glyphs: Vec<Glyph>,
}

#[derive(Clone, Debug)]
pub struct Font {
    /// Имя шрифта из PDF. У текста с картинки имени нет: в скане шрифт не хранится.
    pub name: Option<String>,
    /// Размер в пунктах. Для OCR оценивается по высоте рамки символа.
    pub size: f32,
    pub bold: bool,
    pub italic: bool,
}

#[derive(Clone, Debug)]
pub struct Glyph {
    pub bounds: Rect,
    /// Начало базовой линии.
    pub origin: Point,
    /// Поворот буквы в градусах, как в SVG. Ноль — обычная горизонтальная строка.
    pub rotation: f32,
    pub ch: Option<char>,
    /// Код глифа во встроенном шрифте. У OCR его нет.
    pub glyph_id: Option<u32>,
}

/// Картинка. Скан без текстового слоя — это страница с одним таким элементом на весь лист.
#[derive(Clone, Debug)]
pub struct Image {
    pub bounds: Rect,
    pub pixel_width: u32,
    pub pixel_height: u32,
    /// Фильтр PDF: DCTDecode, CCITTFaxDecode, JBIG2Decode, JPXDecode, FlateDecode.
    pub filter: String,
    pub color_space: String,
    /// Сжатые байты из файла. Для OCR их сначала раскодируют в пиксели.
    pub data: Vec<u8>,
}

/// Линия, прямоугольник или кривая, которые не сведены в таблицу.
#[derive(Clone, Debug)]
pub struct PathShape {
    pub bounds: Rect,
    pub stroke_width: f32,
    pub stroke: Option<Color>,
    pub fill: Option<Color>,
    /// true для заливки `f*` (even-odd). Для `f` поле равно false.
    pub even_odd: bool,
    pub segments: Vec<PathSegment>,
}

#[derive(Clone, Debug)]
pub enum PathSegment {
    Move(Point),
    Line(Point),
    Curve { c1: Point, c2: Point, end: Point },
    Close,
}

/// Таблица. Ширины колонок известны после разбора, а не вычисляются заново при записи HTML.
#[derive(Clone, Debug)]
pub struct Table {
    pub bounds: Rect,
    pub columns: Vec<Column>,
    pub rows: Vec<Row>,
    /// true, если в PDF была нарисована сетка. Таблица только из слов рамки в файле не имела,
    /// поэтому при записи страницы клетки не обводятся.
    pub ruled: bool,
}

#[derive(Clone, Debug)]
pub struct Column {
    /// Ширина колонки в пунктах.
    pub width: f32,
}

#[derive(Clone, Debug)]
pub struct Row {
    pub height: f32,
    pub cells: Vec<Cell>,
}

#[derive(Clone, Debug)]
pub struct Cell {
    pub bounds: Rect,
    pub col_span: u32,
    pub row_span: u32,
    /// Содержимое ячейки в том же наборе элементов, что и страница.
    pub content: Vec<Element>,
}
