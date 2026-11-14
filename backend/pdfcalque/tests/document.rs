use pdfcalque::{document_to_html, Document, Page};

#[test]
fn one_html_file_holds_every_page() {
    let doc = Document {
        pages: vec![
            Page { width: 10.0, height: 20.0, elements: vec![] },
            Page { width: 30.0, height: 40.0, elements: vec![] },
        ],
        title: String::new(),
        language: String::new(),
        outline: vec![],
        faces: vec![],
    };
    let html = document_to_html(&doc);
    assert_eq!(html.matches("<svg ").count(), 2);
    assert!(html.contains("width=\"10.00pt\""));
    assert!(html.contains("width=\"30.00pt\""));
    assert!(html.contains("break-after:page"));
}
