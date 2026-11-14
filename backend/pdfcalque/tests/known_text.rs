//! Точные координаты на PDF, который собирается в тесте.
//! Здесь известно, где стоит каждая буква, поэтому ошибка сдвига видна сразу.

use std::fs;
use std::path::PathBuf;

use lopdf::{dictionary, Document, Object, Stream};
use pdfcalque::{parse_pdf, Element};

#[test]
fn ruled_grid_becomes_a_table_with_column_widths() {
    let doc = parse_pdf(&grid_pdf()).expect("grid");
    let table = doc.pages[0].elements.iter().find_map(|element| match element {
        Element::Table(table) => Some(table),
        _ => None,
    }).expect("table");
    let widths: Vec<f32> = table.columns.iter().map(|column| column.width).collect();
    assert_eq!(widths.len(), 2, "{widths:?}");
    assert!((widths[0] - 70.0).abs() < 1.0, "{widths:?}");
    assert!((widths[1] - 80.0).abs() < 1.0, "{widths:?}");
    let text = table.rows.iter().flat_map(|row| &row.cells).flat_map(|cell| &cell.content).filter_map(|element| match element {
        Element::Text(text) => Some(text.lines[0].spans[0].text.as_str()),
        _ => None,
    }).collect::<Vec<_>>();
    assert!(text.contains(&"A"), "{text:?}");
    assert!(text.contains(&"B"), "{text:?}");
    let csv = pdfcalque::table_to_csv(table);
    assert!(csv.contains("A") && csv.contains("B"), "{csv}");
    assert_eq!(csv.lines().count(), 2);
    let xlsx = pdfcalque::table_to_xlsx(table).expect("xlsx");
    assert!(xlsx.starts_with(b"PK"), "xlsx is a zip file");
    std::fs::write(
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target/preview/grid.xlsx"),
        &xlsx,
    )
    .unwrap();
}

#[test]
fn write_hello_and_grid_html() {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target/preview");
    fs::create_dir_all(&dir).unwrap();
    let hello = sample_pdf();
    fs::write(dir.join("hello.pdf"), &hello).unwrap();
    let parsed = parse_pdf(&hello).unwrap();
    fs::write(dir.join("hello.html"), pdfcalque::page_to_html(&parsed.pages[0])).unwrap();
    let grid = grid_pdf();
    fs::write(dir.join("grid.pdf"), &grid).unwrap();
    let parsed = parse_pdf(&grid).unwrap();
    fs::write(dir.join("grid.html"), pdfcalque::page_to_html(&parsed.pages[0])).unwrap();
}

#[test]
fn hello_is_at_the_requested_point() {
    let doc = parse_pdf(&sample_pdf()).expect("parse");
    let page = &doc.pages[0];
    assert!((page.width - 300.0).abs() < 0.1);
    assert!((page.height - 200.0).abs() < 0.1);

    let text = page.elements.iter().find_map(|element| match element {
        Element::Text(text) => Some(text),
        _ => None,
    }).expect("text");
    let span = &text.lines[0].spans[0];
    assert_eq!(span.text, "Hello");
    assert_eq!(span.font.name.as_deref(), Some("Helvetica"));
    assert!((span.font.size - 12.0).abs() < 0.01, "size {}", span.font.size);
    let origins: Vec<(f32, f32)> = span.glyphs.iter().map(|glyph| (glyph.origin.x, glyph.origin.y)).collect();
    // Ширины заданы в самом PDF: H 722, e 556, l 278, l 278, o 556 на 12 pt.
    let expected = [100.0, 108.664, 115.336, 118.672, 122.008];
    assert_eq!(origins.len(), expected.len());
    for (index, x) in expected.iter().enumerate() {
        assert!((origins[index].0 - x).abs() < 0.05, "glyph {index} x {} != {x}", origins[index].0);
        assert!((origins[index].1 - 80.0).abs() < 0.05, "glyph {index} y {}", origins[index].1);
    }

    let image = page.elements.iter().find_map(|element| match element {
        Element::Image(image) => Some(image),
        _ => None,
    }).expect("image");
    assert!((image.bounds.x - 10.0).abs() < 0.1);
    assert!((image.bounds.y - 20.0).abs() < 0.1);
    assert!((image.bounds.width - 50.0).abs() < 0.1);
    assert!((image.bounds.height - 40.0).abs() < 0.1);
}

fn grid_pdf() -> Vec<u8> {
    let mut doc = Document::with_version("1.4");
    let pages_id = doc.new_object_id();
    let font_id = doc.add_object(dictionary! {
        "Type" => "Font",
        "Subtype" => "Type1",
        "BaseFont" => "Helvetica",
    });
    // Три горизонтали и три вертикали: колонки 70 и 80 пунктов, в ячейках буквы A и B.
    let content = b"50 60 m 200 60 l S 50 80 m 200 80 l S 50 100 m 200 100 l S 50 60 m 50 100 l S 120 60 m 120 100 l S 200 60 m 200 100 l S BT /F1 12 Tf 55 85 Td (A) Tj ET BT /F1 12 Tf 130 65 Td (B) Tj ET";
    let content_id = doc.add_object(Stream::new(dictionary! {}, content.to_vec()));
    let page_id = doc.add_object(dictionary! {
        "Type" => "Page",
        "Parent" => pages_id,
        "MediaBox" => vec![0.into(), 0.into(), 300.into(), 200.into()],
        "Contents" => content_id,
        "Resources" => dictionary! { "Font" => dictionary! { "F1" => font_id } },
    });
    doc.objects.insert(pages_id, Object::Dictionary(dictionary! {
        "Type" => "Pages",
        "Count" => 1,
        "Kids" => vec![page_id.into()],
    }));
    let catalog_id = doc.add_object(dictionary! { "Type" => "Catalog", "Pages" => pages_id });
    doc.trailer.set("Root", catalog_id);
    let mut bytes = Vec::new();
    doc.save_to(&mut bytes).unwrap();
    bytes
}

#[test]
fn words_in_columns_become_a_table_without_rules() {
    let doc = parse_pdf(&plain_grid_pdf()).expect("plain grid");
    let table = doc.pages[0].elements.iter().find_map(|element| match element {
        Element::Table(table) => Some(table),
        _ => None,
    }).expect("table");
    assert!(!table.ruled, "word table must not invent a frame");
    assert_eq!(table.columns.len(), 2);
    assert_eq!(table.rows.len(), 3);
    let csv = pdfcalque::table_to_csv(table);
    for word in ["Red", "Blue", "Green", "1", "2", "3"] {
        assert!(csv.contains(word), "{csv}");
    }
    let outside = doc.pages[0].elements.iter().filter_map(|element| match element {
        Element::Text(text) => Some(text.lines[0].spans[0].text.as_str()),
        _ => None,
    }).collect::<Vec<_>>();
    assert!(outside.contains(&"Note"), "{outside:?}");
    let html = pdfcalque::page_to_html(&doc.pages[0]);
    assert!(!html.contains("stroke=\"#000\""), "borderless table drew a frame");
}

#[test]
fn two_long_columns_stay_paragraphs() {
    let doc = parse_pdf(&two_column_pdf()).expect("columns");
    let tables = doc.pages[0].elements.iter().filter(|element| matches!(element, Element::Table(_))).count();
    assert_eq!(tables, 0);
    let text = doc.pages[0].elements.iter().filter_map(|element| match element {
        Element::Text(text) => Some(text.lines[0].spans[0].text.clone()),
        _ => None,
    }).collect::<Vec<_>>();
    assert!(text.iter().any(|line| line.contains("Columns")), "{text:?}");
}

fn plain_grid_pdf() -> Vec<u8> {
    // Заголовок над сеткой слов. Рамок нет: колонки заданы только координатами.
    let content = b"BT /F1 12 Tf 50 170 Td (Note) Tj ET BT /F1 12 Tf 50 140 Td (Red) Tj ET BT /F1 12 Tf 160 140 Td (1) Tj ET BT /F1 12 Tf 50 120 Td (Blue) Tj ET BT /F1 12 Tf 160 120 Td (2) Tj ET BT /F1 12 Tf 50 100 Td (Green) Tj ET BT /F1 12 Tf 160 100 Td (3) Tj ET";
    page_pdf(content)
}

fn two_column_pdf() -> Vec<u8> {
    let content = b"BT /F1 12 Tf 40 140 Td (Columns of a book stay ordinary text here) Tj ET BT /F1 12 Tf 360 140 Td (Columns of a book stay ordinary text here) Tj ET BT /F1 12 Tf 40 118 Td (Columns of a book stay ordinary text here) Tj ET BT /F1 12 Tf 360 118 Td (Columns of a book stay ordinary text here) Tj ET BT /F1 12 Tf 40 96 Td (Columns of a book stay ordinary text here) Tj ET BT /F1 12 Tf 360 96 Td (Columns of a book stay ordinary text here) Tj ET";
    page_pdf(content)
}

fn page_pdf(content: &[u8]) -> Vec<u8> {
    let mut doc = Document::with_version("1.4");
    let pages_id = doc.new_object_id();
    let font_id = doc.add_object(dictionary! {
        "Type" => "Font",
        "Subtype" => "Type1",
        "BaseFont" => "Helvetica",
    });
    let content_id = doc.add_object(Stream::new(dictionary! {}, content.to_vec()));
    let page_id = doc.add_object(dictionary! {
        "Type" => "Page",
        "Parent" => pages_id,
        "MediaBox" => vec![0.into(), 0.into(), 600.into(), 240.into()],
        "Contents" => content_id,
        "Resources" => dictionary! { "Font" => dictionary! { "F1" => font_id } },
    });
    doc.objects.insert(pages_id, Object::Dictionary(dictionary! {
        "Type" => "Pages",
        "Count" => 1,
        "Kids" => vec![page_id.into()],
    }));
    let catalog_id = doc.add_object(dictionary! { "Type" => "Catalog", "Pages" => pages_id });
    doc.trailer.set("Root", catalog_id);
    let mut bytes = Vec::new();
    doc.save_to(&mut bytes).unwrap();
    bytes
}

fn sample_pdf() -> Vec<u8> {
    let mut doc = Document::with_version("1.4");
    let pages_id = doc.new_object_id();
    // FirstChar = 'H' (72). Дальше до 'o' (111) лежат ширины в тысячных em.
    let mut widths = vec![500.0_f32; 40];
    widths[0] = 722.0; // H
    widths[101 - 72] = 556.0; // e
    widths[108 - 72] = 278.0; // l
    widths[111 - 72] = 556.0; // o
    let font_id = doc.add_object(dictionary! {
        "Type" => "Font",
        "Subtype" => "Type1",
        "BaseFont" => "Helvetica",
        "FirstChar" => 72,
        "Widths" => widths.into_iter().map(|w| Object::Real(w)).collect::<Vec<_>>(),
    });
    let image_id = doc.add_object(Stream::new(dictionary! {
        "Type" => "XObject",
        "Subtype" => "Image",
        "Width" => 1,
        "Height" => 1,
        "ColorSpace" => "DeviceGray",
        "BitsPerComponent" => 8,
    }, vec![255]));
    let content = b"q 50 0 0 40 10 20 cm /Im0 Do Q BT /F1 12 Tf 100 80 Td (Hello) Tj ET";
    let content_id = doc.add_object(Stream::new(dictionary! {}, content.to_vec()));
    let page_id = doc.add_object(dictionary! {
        "Type" => "Page",
        "Parent" => pages_id,
        "MediaBox" => vec![0.into(), 0.into(), 300.into(), 200.into()],
        "Contents" => content_id,
        "Resources" => dictionary! {
            "Font" => dictionary! { "F1" => font_id },
            "XObject" => dictionary! { "Im0" => image_id },
        },
    });
    doc.objects.insert(pages_id, Object::Dictionary(dictionary! {
        "Type" => "Pages",
        "Count" => 1,
        "Kids" => vec![page_id.into()],
    }));
    let catalog_id = doc.add_object(dictionary! { "Type" => "Catalog", "Pages" => pages_id });
    doc.trailer.set("Root", catalog_id);
    let mut bytes = Vec::new();
    doc.save_to(&mut bytes).unwrap();
    bytes
}
