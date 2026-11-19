//! PDFCalque разбирает PDF в собственные структуры.
//!
//! По этим структурам потом собирается документ в нужном формате. Первым будет HTML.
//!
//! Обычный PDF разбирается по файлу: объекты, команды страницы, шрифты, координаты.
//! Скан остаётся картинкой страницы. Если букв в файле нет, поверх картинки
//! кладётся невидимый текст в тех же местах, чтобы его можно было выделить.

mod ccitt;
mod csv;
mod epub;
mod geom;
mod html;
mod otf;
mod model;
mod ocr;
mod parse;
mod xlsx;

pub use csv::table_to_csv;
pub use epub::{document_to_epub, write_epub};
pub use geom::{Color, Point, Rect};
pub use html::{document_to_html, page_to_html, write_document, write_html};
pub use ocr::maybe_scan as ocr_scan;
pub use xlsx::table_to_xlsx;
pub use parse::{parse_pdf, parse_pdf_page};

pub use model::{
    Cell, Column, Document, Element, Face, Font, Glyph, Heading, Image, Page, PathSegment, PathShape, Row,
    Table, TextBlock, TextLine, TextSource, TextSpan,
};
