#!/usr/bin/env python3
"""
HTML Generator for PDF Pages
Creates interactive HTML pages with selectable text overlaid on page images.
"""
import os
import json
from typing import Dict, List, Optional
import pdfplumber
from PIL import Image


class HTMLPageGenerator:
    """
    Generates interactive HTML pages from PDF data.
    """
    
    def __init__(self):
        """Initialize the HTML generator."""
        pass
    
    def extract_detailed_text_data(self, pdf_path: str) -> List[Dict]:
        """Extract detailed text positioning data from PDF."""
        pages_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"Extracting detailed data from page {page_num}...")
                    
                    # Get page dimensions
                    page_width = page.width
                    page_height = page.height
                    
                    # Extract characters with detailed positioning
                    chars_data = []
                    try:
                        chars = page.chars
                        current_word = ""
                        word_chars = []
                        
                        for i, char in enumerate(chars):
                            char_data = {
                                'text': char.get('text', ''),
                                'x0': char.get('x0', 0),
                                'y0': char.get('y0', 0),
                                'x1': char.get('x1', 0),
                                'y1': char.get('y1', 0),
                                'width': char.get('width', 0),
                                'height': char.get('height', 0),
                                'size': char.get('size', 12),
                                'fontname': char.get('fontname', 'Arial')
                            }
                            
                            # Group characters into words
                            if char_data['text'].strip():
                                word_chars.append(char_data)
                                current_word += char_data['text']
                            else:
                                # Space or whitespace - end current word
                                if word_chars:
                                    # Calculate word bounding box
                                    word_x0 = min(c['x0'] for c in word_chars)
                                    word_y0 = min(c['y0'] for c in word_chars)
                                    word_x1 = max(c['x1'] for c in word_chars)
                                    word_y1 = max(c['y1'] for c in word_chars)
                                    
                                    chars_data.append({
                                        'text': current_word,
                                        'x0': word_x0,
                                        'y0': word_y0,
                                        'x1': word_x1,
                                        'y1': word_y1,
                                        'width': word_x1 - word_x0,
                                        'height': word_y1 - word_y0,
                                        'size': word_chars[0]['size'],
                                        'fontname': word_chars[0]['fontname'],
                                        'type': 'word'
                                    })
                                
                                current_word = ""
                                word_chars = []
                        
                        # Handle last word if any
                        if word_chars:
                            word_x0 = min(c['x0'] for c in word_chars)
                            word_y0 = min(c['y0'] for c in word_chars)
                            word_x1 = max(c['x1'] for c in word_chars)
                            word_y1 = max(c['y1'] for c in word_chars)
                            
                            chars_data.append({
                                'text': current_word,
                                'x0': word_x0,
                                'y0': word_y0,
                                'x1': word_x1,
                                'y1': word_y1,
                                'width': word_x1 - word_x0,
                                'height': word_y1 - word_y0,
                                'size': word_chars[0]['size'],
                                'fontname': word_chars[0]['fontname'],
                                'type': 'word'
                            })
                    
                    except Exception as e:
                        print(f"Error extracting character data: {e}")
                        chars_data = []
                    
                    # Extract full text as fallback
                    full_text = page.extract_text() or ""
                    
                    pages_data.append({
                        'page_number': page_num,
                        'width': page_width,
                        'height': page_height,
                        'text_elements': chars_data,
                        'full_text': full_text,
                        'word_count': len(full_text.split()) if full_text else 0
                    })
        
        except Exception as e:
            print(f"Error extracting detailed text data: {e}")
        
        return pages_data

    def generate_page_html(self, page_data: Dict, image_path: str, output_path: str) -> str:
        """Generate HTML for a single page."""
        page_num = page_data['page_number']
        page_width = page_data['width']
        page_height = page_data['height']
        text_elements = page_data.get('text_elements', [])
        
        # Convert absolute path to relative for HTML
        rel_image_path = os.path.relpath(image_path, os.path.dirname(output_path))
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Page {page_num}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
        }}
        
        .page-wrapper {{
            max-width: 100%;
            margin: 0 auto;
            position: relative;
            display: inline-block;
        }}
        
        .page-container {{
            position: relative;
            width: 100%;
            max-width: 100vw;
            margin: 0 auto;
            border: 1px solid #ccc;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background: white;
        }}
        
        .page-image {{
            width: 100%;
            height: auto;
            display: block;
            user-select: none;
        }}
        
        .text-layer {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
        }}
        
        .text-element {{
            position: absolute;
            cursor: text;
            user-select: text;
            pointer-events: auto;
            color: transparent;
            z-index: 10;
            padding: 1px;
            margin: 0;
            line-height: 1;
            white-space: nowrap;
            background-color: transparent;
            font-family: 'Times', serif;
            border: none;
            transform-origin: left top;
            overflow: visible;
            min-width: 8px;
            min-height: 8px;
        }}
        
        .text-element:hover {{
            /* Completely invisible hover - no visual feedback */
        }}
        
        .text-element.selected {{
            background-color: rgba(0, 123, 255, 0.15);
            color: transparent;
            border: none;
            z-index: 20;
        }}
        
        .controls {{
            text-align: center;
            margin-bottom: 20px;
        }}
        
        .toggle-text {{
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 0 10px;
        }}
        
        .toggle-text:hover {{
            background-color: #0056b3;
        }}
        
        .show-text .text-element {{
            color: rgba(0, 0, 0, 0.7) !important;
            background-color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.3) !important;
        }}
        
        .debug-mode .text-element {{
            color: rgba(0, 0, 0, 0.8) !important;
            background-color: rgba(255, 255, 255, 0.9);
            border: 2px solid rgba(255, 0, 0, 0.8) !important;
            box-shadow: 0 0 2px rgba(255, 0, 0, 0.5);
        }}
        
        .info {{
            text-align: center;
            margin-bottom: 20px;
            padding: 10px;
            background-color: white;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .toggle-text {{ 
                padding: 8px 16px; 
                margin: 5px;
                font-size: 14px;
            }}
        }}
    </style>
</head>
<body>
    <div class="info">
        <h2>📄 PDF Page {page_num}</h2>
        <p>Original size: {page_width:.0f} × {page_height:.0f} pts | Text elements: {len(text_elements)}</p>
        <p>🎯 Responsive positioning - scales with page size</p>
    </div>
    
    <div class="controls">
        <button class="toggle-text" onclick="toggleTextVisibility()">Toggle Text Visibility</button>
        <button class="toggle-text" onclick="toggleDebugMode()">Debug Mode (Show Text Boxes)</button>
        <button class="toggle-text" onclick="selectAllText()">Select All Text</button>
        <button class="toggle-text" onclick="copySelectedText()">Copy Selected</button>
        <a href="index.html" class="toggle-text" style="text-decoration: none;">← Back to Index</a>
    </div>
    
    <div class="page-wrapper">
        <div class="page-container" id="pageContainer">
            <img src="{rel_image_path}" alt="PDF Page {page_num}" class="page-image"/>
            <div class="text-layer">
'''
        
        # Add text elements with percentage-based positioning
        for i, element in enumerate(text_elements):
            # Calculate percentage positions (responsive to any scale)
            left_percent = (element['x0'] / page_width) * 100
            
            # Adjust for font ascent - PDF baseline vs HTML top positioning
            # Use y1 (top of text) instead of y0 (baseline) for better alignment
            top_percent = ((page_height - element['y1']) / page_height) * 100  # Flip Y and use top
            width_percent = ((element['x1'] - element['x0']) / page_width) * 100
            height_percent = ((element['y1'] - element['y0']) / page_height) * 100  # Actual text height
            
            # Font size as percentage of page height for scalability
            font_size_percent = (element['size'] / page_height) * 100
            
            text = element['text'].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;').replace('"', '&quot;')
            
            html_content += f'''                <span class="text-element" 
                      style="left: {left_percent:.3f}%; 
                             top: {top_percent:.3f}%; 
                             width: {width_percent:.3f}%; 
                             height: {height_percent:.3f}%;
                             font-size: {font_size_percent:.3f}vh;"
                      data-text="{text}"
                      data-pdf-coords="x0={element['x0']:.1f},y0={element['y0']:.1f},y1={element['y1']:.1f},size={element['size']:.1f}"></span>
'''
        
        html_content += '''            </div>
        </div>
    </div>
    
    <script>
        let textVisible = false;
        let debugMode = false;
        let selectedElements = new Set();
        
        function toggleTextVisibility() {
            const container = document.getElementById('pageContainer');
            textVisible = !textVisible;
            
            if (textVisible) {
                container.classList.add('show-text');
            } else {
                container.classList.remove('show-text');
            }
        }
        
        function toggleDebugMode() {
            const container = document.getElementById('pageContainer');
            debugMode = !debugMode;
            
            if (debugMode) {
                container.classList.add('debug-mode');
            } else {
                container.classList.remove('debug-mode');
            }
        }
        
        function selectAllText() {
            const elements = document.querySelectorAll('.text-element');
            selectedElements.clear();
            
            elements.forEach(element => {
                element.classList.add('selected');
                selectedElements.add(element);
            });
        }
        
        function copySelectedText() {
            const texts = Array.from(selectedElements)
                .sort((a, b) => {
                    const aTop = parseFloat(a.style.top);
                    const bTop = parseFloat(b.style.top);
                    if (Math.abs(aTop - bTop) < 1) {
                        return parseFloat(a.style.left) - parseFloat(b.style.left);
                    }
                    return aTop - bTop;
                })
                .map(el => el.getAttribute('data-text'))
                .join(' ');
            
            if (texts) {
                navigator.clipboard.writeText(texts).then(() => {
                    alert('Text copied to clipboard!');
                }).catch(err => {
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = texts;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    alert('Text copied to clipboard!');
                });
            }
        }
        
        // Enhanced text selection functionality
        let isSelecting = false;
        let isDragging = false;
        let startX, startY;
        let selectionBox;
        let lastSelectedElement = null;
        
        // Clear all selections
        function clearSelection() {
            selectedElements.forEach(element => {
                element.classList.remove('selected');
            });
            selectedElements.clear();
        }
        
        // Handle multi-selection with Ctrl/Cmd + click
        document.addEventListener('click', function(e) {
            // Only handle Ctrl/Cmd clicks here, regular clicks are handled in mouseup
            if (e.target.classList.contains('text-element') && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                e.stopPropagation();
                
                // Toggle selection of clicked element (multi-select mode)
                if (selectedElements.has(e.target)) {
                    e.target.classList.remove('selected');
                    selectedElements.delete(e.target);
                } else {
                    e.target.classList.add('selected');
                    selectedElements.add(e.target);
                }
                
                lastSelectedElement = e.target;
            }
        });
        
        // Double-click to select word and nearby words
        document.addEventListener('dblclick', function(e) {
            if (e.target.classList.contains('text-element')) {
                e.preventDefault();
                clearSelection();
                
                // Select the double-clicked element
                e.target.classList.add('selected');
                selectedElements.add(e.target);
                
                // Find and select nearby words on the same line
                const clickedRect = e.target.getBoundingClientRect();
                const elements = document.querySelectorAll('.text-element');
                
                elements.forEach(element => {
                    if (element !== e.target) {
                        const elementRect = element.getBoundingClientRect();
                        const verticalOverlap = Math.abs(clickedRect.top - elementRect.top) < 5;
                        const horizontalDistance = Math.abs(clickedRect.left - elementRect.left);
                        
                        // Select elements on the same line within reasonable distance
                        if (verticalOverlap && horizontalDistance < 200) {
                            element.classList.add('selected');
                            selectedElements.add(element);
                        }
                    }
                });
            }
        });
        
        // Enhanced drag selection
        document.addEventListener('mousedown', function(e) {
            // Start selection if clicking on page container area OR text elements
            if (e.target.classList.contains('text-layer') || 
                e.target.classList.contains('page-image') || 
                e.target.classList.contains('page-container') ||
                e.target.classList.contains('text-element')) {
                
                isSelecting = true;
                isDragging = false;
                startX = e.clientX;
                startY = e.clientY;
                
                // Don't clear selection immediately, wait to see if it's a drag
                
                e.preventDefault();
            }
        });
        
        document.addEventListener('mousemove', function(e) {
            if (isSelecting) {
                const currentX = e.clientX;
                const currentY = e.clientY;
                const distance = Math.sqrt(Math.pow(currentX - startX, 2) + Math.pow(currentY - startY, 2));
                
                // Start showing selection box after moving at least 5 pixels
                if (distance > 5) {
                    isDragging = true;
                    
                    if (!selectionBox) {
                        selectionBox = document.createElement('div');
                        selectionBox.style.position = 'fixed';
                        selectionBox.style.border = '2px solid #007bff';
                        selectionBox.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
                        selectionBox.style.pointerEvents = 'none';
                        selectionBox.style.zIndex = '1000';
                        selectionBox.style.borderRadius = '2px';
                        document.body.appendChild(selectionBox);
                    }
                    
                    const left = Math.min(startX, currentX);
                    const top = Math.min(startY, currentY);
                    const width = Math.abs(currentX - startX);
                    const height = Math.abs(currentY - startY);
                    
                    selectionBox.style.left = left + 'px';
                    selectionBox.style.top = top + 'px';
                    selectionBox.style.width = width + 'px';
                    selectionBox.style.height = height + 'px';
                    
                    // Real-time selection highlighting
                    if (width > 10 && height > 10) {
                        const rect = selectionBox.getBoundingClientRect();
                        const elements = document.querySelectorAll('.text-element');
                        
                        elements.forEach(element => {
                            const elementRect = element.getBoundingClientRect();
                            const isInSelection = elementRect.left < rect.right && 
                                                 elementRect.right > rect.left && 
                                                 elementRect.top < rect.bottom && 
                                                 elementRect.bottom > rect.top;
                            
                            if (isInSelection && !selectedElements.has(element)) {
                                element.classList.add('selected');
                                selectedElements.add(element);
                            } else if (!isInSelection && selectedElements.has(element) && !e.ctrlKey && !e.metaKey) {
                                element.classList.remove('selected');
                                selectedElements.delete(element);
                            }
                        });
                    }
                }
            }
        });
        
        document.addEventListener('mouseup', function(e) {
            if (isSelecting) {
                if (selectionBox) {
                    document.body.removeChild(selectionBox);
                    selectionBox = null;
                }
                
                // If this was just a click (no drag), handle single selection
                if (!isDragging && e.target.classList.contains('text-element')) {
                    // Clear previous selection if not holding Ctrl/Cmd
                    if (!e.ctrlKey && !e.metaKey) {
                        clearSelection();
                    }
                    
                    // Toggle selection of clicked element
                    if (selectedElements.has(e.target)) {
                        e.target.classList.remove('selected');
                        selectedElements.delete(e.target);
                    } else {
                        e.target.classList.add('selected');
                        selectedElements.add(e.target);
                    }
                } else if (!isDragging) {
                    // Clicked on empty area without dragging
                    if (!e.ctrlKey && !e.metaKey) {
                        clearSelection();
                    }
                }
                
                isSelecting = false;
                isDragging = false;
                
                // Auto-copy selection if text was selected
                if (selectedElements.size > 0) {
                    // Show a subtle notification
                    showSelectionNotification();
                }
            }
        });
        
        // Show notification when text is selected
        function showSelectionNotification() {
            const notification = document.createElement('div');
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.background = '#007bff';
            notification.style.color = 'white';
            notification.style.padding = '10px 15px';
            notification.style.borderRadius = '4px';
            notification.style.zIndex = '2000';
            notification.style.fontSize = '14px';
            notification.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
            notification.textContent = `${selectedElements.size} text elements selected. Press Ctrl+C or click Copy button.`;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 3000);
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'a') {
                    e.preventDefault();
                    selectAllText();
                } else if (e.key === 'c' && selectedElements.size > 0) {
                    e.preventDefault();
                    copySelectedText();
                }
            } else if (e.key === 'Escape') {
                clearSelection();
            }
        });
        
        // Handle window resize to maintain positioning
        window.addEventListener('resize', function() {
            // Text elements automatically adjust due to percentage positioning
            console.log('Window resized - text positions automatically adjusted');
        });
    </script>
</body>
</html>'''
        
        # Save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Generated HTML: {output_path}")
        return output_path

    def generate_html_pages(self, pdf_path: str, image_dir: str, output_dir: str = "html_pages") -> List[str]:
        """Generate HTML pages for all pages in the PDF."""
        print(f"🌐 Generating interactive HTML pages...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract detailed text data
        pages_data = self.extract_detailed_text_data(pdf_path)
        
        html_files = []
        
        for page_data in pages_data:
            page_num = page_data['page_number']
            
            # Find corresponding image
            image_path = os.path.join(image_dir, f"page_{page_num:03d}.png")
            
            if not os.path.exists(image_path):
                print(f"⚠️  Warning: Image not found for page {page_num}: {image_path}")
                continue
            
            # Generate HTML file
            html_filename = f"page_{page_num:03d}.html"
            html_path = os.path.join(output_dir, html_filename)
            
            self.generate_page_html(page_data, image_path, html_path)
            html_files.append(html_path)
        
        # Generate index page
        self.generate_index_page(html_files, output_dir, pdf_path)
        
        return html_files

    def generate_index_page(self, html_files: List[str], output_dir: str, pdf_path: str):
        """Generate an index page linking to all HTML pages."""
        index_path = os.path.join(output_dir, "index.html")
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Pages - {os.path.basename(pdf_path)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .header {{
            text-align: center;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .pages-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .page-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }}
        
        .page-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        
        .page-link {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
        }}
        
        .page-link:hover {{
            background-color: #0056b3;
        }}
        
        .stats {{
            background-color: #e8f4fd;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 Interactive PDF Pages</h1>
        <h2>{os.path.basename(pdf_path)}</h2>
        <div class="stats">
            <strong>Total Pages:</strong> {len(html_files)} | 
            <strong>All pages have selectable text overlays</strong>
        </div>
        <p>Click on any page below to view it with selectable text overlay</p>
    </div>
    
    <div class="pages-grid">
'''
        
        for i, html_file in enumerate(html_files, 1):
            filename = os.path.basename(html_file)
            html_content += f'''        <div class="page-card">
            <h3>📄 Page {i}</h3>
            <p>Interactive page with selectable text</p>
            <a href="{filename}" class="page-link">View Page {i}</a>
        </div>
'''
        
        html_content += '''    </div>
    
    <div style="text-align: center; margin-top: 40px; padding: 20px; background: white; border-radius: 8px;">
        <h3>🔧 Features</h3>
        <ul style="text-align: left; display: inline-block;">
            <li><strong>Toggle Text Visibility:</strong> Show/hide text overlay</li>
            <li><strong>Click Selection:</strong> Click individual words to select</li>
            <li><strong>Drag Selection:</strong> Drag to select multiple words</li>
            <li><strong>Copy Text:</strong> Copy selected text to clipboard</li>
            <li><strong>Select All:</strong> Select all text on the page</li>
        </ul>
    </div>
</body>
</html>'''
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 Generated index page: {index_path}")


def main():
    """Generate interactive HTML pages."""
    generator = HTMLPageGenerator()
    
    pdf_file = "sample1.pdf"
    image_dir = "alternative_output"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file '{pdf_file}' not found!")
        return
    
    if not os.path.exists(image_dir):
        print(f"❌ Image directory '{image_dir}' not found!")
        print("Please run the alternative parser first to generate page images.")
        return
    
    try:
        html_files = generator.generate_html_pages(pdf_file, image_dir)
        
        print(f"\n✅ Generated {len(html_files)} interactive HTML pages!")
        print(f"📂 Open html_pages/index.html in your browser to start")
        print(f"🌐 Individual pages:")
        for html_file in html_files:
            print(f"   - {html_file}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
