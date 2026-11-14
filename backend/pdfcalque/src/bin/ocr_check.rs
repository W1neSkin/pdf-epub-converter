//! Печатает строки OCR для одной JPEG-страницы скана.

fn main() {
    let path = std::env::args().nth(1).expect("jpeg");
    let jpeg = std::fs::read(&path).expect("read");
    let mut elements = vec![pdfcalque::Element::Image(pdfcalque::Image {
        bounds: pdfcalque::Rect { x: 0.0, y: 0.0, width: 612.0, height: 792.0 },
        pixel_width: 2550,
        pixel_height: 3300,
        filter: "DCTDecode".into(),
        color_space: "DeviceRGB".into(),
        data: jpeg,
    })];
    pdfcalque::ocr_scan(&mut elements, 612.0, 792.0);
    for element in &elements {
        if let pdfcalque::Element::Text(text) = element {
            println!("{}", text.lines[0].spans[0].text);
        }
    }
}
