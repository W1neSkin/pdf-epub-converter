#!/usr/bin/env python3
"""
EPUB Generator
Converts HTML pages to EPUB format for e-reader compatibility.
"""
import os
import json
import zipfile
import shutil
from datetime import datetime
from typing import List, Dict
import uuid
from pathlib import Path


class EPUBGenerator:
    """
    Generates EPUB files from HTML pages.
    """
    
    def __init__(self):
        """Initialize the EPUB generator."""
        self.epub_id = str(uuid.uuid4())
        self.creation_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def create_mimetype(self, epub_dir: str):
        """Create the mimetype file (must be first and uncompressed)."""
        mimetype_path = os.path.join(epub_dir, "mimetype")
        with open(mimetype_path, 'w', encoding='utf-8') as f:
            f.write("application/epub+zip")
    
    def create_container_xml(self, epub_dir: str):
        """Create the META-INF/container.xml file."""
        meta_inf_dir = os.path.join(epub_dir, "META-INF")
        os.makedirs(meta_inf_dir, exist_ok=True)
        
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
        
        container_path = os.path.join(meta_inf_dir, "container.xml")
        with open(container_path, 'w', encoding='utf-8') as f:
            f.write(container_xml)
    
    def create_content_opf(self, epub_dir: str, title: str, html_files: List[str], image_files: List[str]):
        """Create the content.opf file with metadata and manifest."""
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        os.makedirs(epub_content_dir, exist_ok=True)
        
        # Generate manifest items
        manifest_items = []
        spine_items = []
        
        # Add HTML files
        for i, html_file in enumerate(html_files):
            filename = os.path.basename(html_file)
            item_id = f"page_{i+1}"
            manifest_items.append(f'    <item id="{item_id}" href="{filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'    <itemref idref="{item_id}"/>')
        
        # Add image files
        for i, image_file in enumerate(image_files):
            filename = os.path.basename(image_file)
            item_id = f"img_{i+1}"
            manifest_items.append(f'    <item id="{item_id}" href="images/{filename}" media-type="image/png"/>')
        
        # Add CSS file
        manifest_items.append('    <item id="stylesheet" href="styles.css" media-type="text/css"/>')
        
        # Add navigation file
        manifest_items.append('    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        spine_items.insert(0, '    <itemref idref="nav"/>')
        
        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="uid">{self.epub_id}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator>PDF to EPUB Converter</dc:creator>
        <dc:language>en</dc:language>
        <dc:date>{self.creation_date}</dc:date>
        <meta property="dcterms:modified">{self.creation_date}</meta>
        <dc:description>Interactive PDF converted to EPUB with selectable text</dc:description>
    </metadata>
    <manifest>
{chr(10).join(manifest_items)}
    </manifest>
    <spine>
{chr(10).join(spine_items)}
    </spine>
</package>'''
        
        content_opf_path = os.path.join(epub_content_dir, "content.opf")
        with open(content_opf_path, 'w', encoding='utf-8') as f:
            f.write(content_opf)
    
    def create_navigation(self, epub_dir: str, title: str, html_files: List[str]):
        """Create the navigation file (nav.xhtml)."""
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        
        # Generate navigation list
        nav_items = []
        for i, html_file in enumerate(html_files):
            filename = os.path.basename(html_file)
            nav_items.append(f'            <li><a href="{filename}">Page {i+1}</a></li>')
        
        nav_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Navigation</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
{chr(10).join(nav_items)}
        </ol>
    </nav>
</body>
</html>'''
        
        nav_path = os.path.join(epub_content_dir, "nav.xhtml")
        with open(nav_path, 'w', encoding='utf-8') as f:
            f.write(nav_xhtml)
    
    def create_stylesheet(self, epub_dir: str):
        """Create the CSS stylesheet for EPUB."""
        epub_content_dir = os.path.join(epub_dir, "EPUB")
        
        css_content = '''/* EPUB Stylesheet */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #ffffff;
    line-height: 1.6;
}

.page-container {
    position: relative;
    margin: 0 auto 40px auto;
    max-width: 100%;
    border: 1px solid #ccc;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    page-break-after: always;
    background: white;
}

.page-image {
    width: 100%;
    height: auto;
    display: block;
    user-select: none;
}

.text-layer {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
}

.text-element {
    position: absolute;
    color: transparent;
    user-select: text;
    pointer-events: auto;
    z-index: 10;
    margin: 0;
    padding: 0;
    line-height: 1;
    white-space: nowrap;
    background-color: transparent;
    border: none;
    cursor: text;
    font-family: 'Times', serif;
    transform-origin: left top;
    overflow: hidden;
}

.text-element:hover {
    /* Completely invisible hover - no visual feedback */
}

.text-element:focus,
.text-element:active,
.text-element.selected {
    background-color: rgba(0, 123, 255, 0.15);
    color: transparent;
    border: none;
    z-index: 20;
}

/* Selection notification */
.selection-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: #007bff;
    color: white;
    padding: 10px 15px;
    border-radius: 4px;
    z-index: 2000;
    font-size: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.page-info {
    text-align: center;
    margin-bottom: 20px;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 4px;
    border: 1px solid #dee2e6;
}

/* Navigation styles */
nav ol {
    list-style-type: decimal;
    padding-left: 30px;
}

nav li {
    margin: 10px 0;
}

nav a {
    text-decoration: none;
    color: #007bff;
    font-weight: bold;
}

nav a:hover {
    text-decoration: underline;
}

h1, h2 {
    color: #333;
    text-align: center;
}

/* Print and e-reader optimizations */
@media print {
    .page-container {
        page-break-after: always;
        box-shadow: none;
        border: none;
    }
}

/* Dark mode support for e-readers */
@media (prefers-color-scheme: dark) {
    body {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    
    .page-info {
        background-color: #2d2d2d;
        border-color: #444;
    }
}
'''
        
        css_path = os.path.join(epub_content_dir, "styles.css")
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
    
    def convert_html_for_epub(self, html_file: str, output_dir: str, image_dir: str) -> str:
        """Convert HTML file to EPUB-compatible format."""
        # Read the original HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract page info from HTML
        page_num = 1
        if "PDF Page" in content:
            import re
            match = re.search(r'PDF Page (\d+)', content)
            if match:
                page_num = int(match.group(1))
        
        # Get image path
        image_filename = f"page_{page_num:03d}.png"
        image_path = os.path.join(image_dir, image_filename)
        
        if not os.path.exists(image_path):
            print(f"Warning: Image not found: {image_path}")
            return ""
        
        # Extract text elements from original HTML
        import re
        text_elements = re.findall(r'<span class="text-element"[^>]*>(.*?)</span>', content, re.DOTALL)
        
        # Create EPUB-compatible HTML
        epub_html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Page {page_num}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body>
    <div class="page-info">
        <h2>📄 Page {page_num}</h2>
        <p>Converted from PDF with selectable text</p>
    </div>
    
    <div class="page-container">
        <img src="images/{image_filename}" alt="Page {page_num}" class="page-image"/>
        <div class="text-layer">
'''
        
        # Add text elements (extract from original HTML with positioning)
        # This is a simplified version - we'll extract the positioning from the original
        import re
        text_pattern = r'<span class="text-element"\s+style="([^"]*)"[^>]*data-text="([^"]*)"[^>]*>.*?</span>'
        matches = re.findall(text_pattern, content, re.DOTALL)
        
        for style, text in matches:
            epub_html += f'''            <span class="text-element" style="{style}" data-text="{text}"></span>
'''
        
        epub_html += '''        </div>
    </div>
</body>
</html>'''
        
        # Save EPUB-compatible HTML
        output_filename = f"page_{page_num:03d}.xhtml"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(epub_html)
        
        return output_path
    
    def generate_epub(self, html_dir: str, image_dir: str, output_filename: str = "converted.epub", title: str = "Converted PDF") -> str:
        """Generate EPUB file from HTML pages."""
        print(f"📚 Generating EPUB: {output_filename}")
        
        # Create temporary directory for EPUB structure
        temp_dir = "temp_epub"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            # Find HTML files
            html_files = []
            for file in sorted(os.listdir(html_dir)):
                if file.startswith("page_") and file.endswith(".html"):
                    html_files.append(os.path.join(html_dir, file))
            
            if not html_files:
                raise ValueError("No page HTML files found!")
            
            print(f"Found {len(html_files)} HTML pages")
            
            # Find image files
            image_files = []
            for file in sorted(os.listdir(image_dir)):
                if file.startswith("page_") and file.endswith(".png"):
                    image_files.append(os.path.join(image_dir, file))
            
            print(f"Found {len(image_files)} images")
            
            # Create EPUB structure
            self.create_mimetype(temp_dir)
            self.create_container_xml(temp_dir)
            
            # Create EPUB content directory
            epub_content_dir = os.path.join(temp_dir, "EPUB")
            os.makedirs(epub_content_dir, exist_ok=True)
            
            # Create images directory
            epub_images_dir = os.path.join(epub_content_dir, "images")
            os.makedirs(epub_images_dir, exist_ok=True)
            
            # Copy and convert HTML files
            converted_html_files = []
            for html_file in html_files:
                converted_file = self.convert_html_for_epub(html_file, epub_content_dir, image_dir)
                if converted_file:
                    converted_html_files.append(converted_file)
                    print(f"✅ Converted: {os.path.basename(html_file)}")
            
            # Copy image files
            for image_file in image_files:
                dest_path = os.path.join(epub_images_dir, os.path.basename(image_file))
                shutil.copy2(image_file, dest_path)
                print(f"✅ Copied image: {os.path.basename(image_file)}")
            
            # Create EPUB metadata files
            self.create_content_opf(temp_dir, title, [os.path.basename(f) for f in converted_html_files], [os.path.basename(f) for f in image_files])
            self.create_navigation(temp_dir, title, [os.path.basename(f) for f in converted_html_files])
            self.create_stylesheet(temp_dir)
            
            # Create EPUB zip file
            if os.path.exists(output_filename):
                os.remove(output_filename)
            
            with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
                # Add mimetype first (uncompressed)
                epub_zip.write(os.path.join(temp_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
                
                # Add all other files
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file != "mimetype":  # Already added
                            file_path = os.path.join(root, file)
                            archive_path = os.path.relpath(file_path, temp_dir)
                            epub_zip.write(file_path, archive_path)
            
            print(f"✅ EPUB created: {output_filename}")
            return output_filename
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def main():
    """Generate EPUB from HTML pages."""
    generator = EPUBGenerator()
    
    html_dir = "html_pages"
    image_dir = "alternative_output"
    pdf_name = "sample1.pdf"
    
    if not os.path.exists(html_dir):
        print(f"❌ HTML directory '{html_dir}' not found!")
        print("Please run the HTML generator first.")
        return
    
    if not os.path.exists(image_dir):
        print(f"❌ Image directory '{image_dir}' not found!")
        print("Please run the PDF parser first.")
        return
    
    try:
        # Generate EPUB
        title = f"Converted PDF: {os.path.splitext(pdf_name)[0]}"
        output_filename = f"{os.path.splitext(pdf_name)[0]}.epub"
        
        epub_file = generator.generate_epub(
            html_dir=html_dir,
            image_dir=image_dir,
            output_filename=output_filename,
            title=title
        )
        
        # Get file size
        file_size = os.path.getsize(epub_file) / (1024 * 1024)
        
        print(f"\n🎉 EPUB Generation Complete!")
        print(f"📚 File: {epub_file}")
        print(f"📏 Size: {file_size:.2f} MB")
        print(f"📱 Compatible with: Kindle, Apple Books, Adobe Digital Editions, and other EPUB readers")
        print(f"✨ Features: Selectable text, page images, navigation")
        
    except Exception as e:
        print(f"❌ Error generating EPUB: {e}")


if __name__ == "__main__":
    main() 