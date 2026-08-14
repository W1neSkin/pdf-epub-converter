#!/usr/bin/env python3
"""
Alternative PDF Parser using Python libraries instead of browser automation.
This approach is much more reliable and faster.
"""
import os
import json
from typing import Dict, List, Optional
import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import PyPDF2


class AlternativePDFParser:
    """
    PDF Parser using Python libraries - no browser required!
    """
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def extract_text_pdfplumber(self, pdf_path: str, on_progress=None) -> List[Dict]:
        """Extract text using pdfplumber (best for text extraction)."""
        pages_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    text = page.extract_text() or ""
                    
                    # Get page dimensions
                    width = page.width if hasattr(page, 'width') else 0
                    height = page.height if hasattr(page, 'height') else 0
                    
                    # Extract text with coordinates (if available)
                    text_elements = []
                    try:
                        chars = page.chars
                        for char in chars[:100]:  # Limit to first 100 chars for demo
                            text_elements.append({
                                'text': char.get('text', ''),
                                'x': char.get('x0', 0),
                                'y': char.get('y0', 0),
                                'fontsize': char.get('size', 12)
                            })
                    except:
                        pass
                    
                    pages_data.append({
                        'page_number': page_num,
                        'text': text,
                        'word_count': len(text.split()) if text else 0,
                        'width': width,
                        'height': height,
                        'text_elements': text_elements[:20]  # First 20 elements
                    })
                    
                    print(f"Extracted text from page {page_num}: {len(text)} characters")
                    if on_progress and total:
                        percent = 10 + int(20 * page_num / total)
                        on_progress(
                            percent,
                            f"Extracting text from page {page_num} of {total}",
                            page_num,
                            total,
                        )
        
        except Exception as e:
            print(f"Error with pdfplumber: {e}")
        
        return pages_data
    
    def extract_text_pypdf2(self, pdf_path: str) -> List[Dict]:
        """Extract text using PyPDF2 (fallback method)."""
        pages_data = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        
                        pages_data.append({
                            'page_number': page_num,
                            'text': text,
                            'word_count': len(text.split()) if text else 0
                        })
                        
                        print(f"PyPDF2 extracted from page {page_num}: {len(text)} characters")
                    except Exception as e:
                        print(f"Error extracting page {page_num} with PyPDF2: {e}")
                        pages_data.append({
                            'page_number': page_num,
                            'text': '',
                            'word_count': 0,
                            'error': str(e)
                        })
        
        except Exception as e:
            print(f"Error with PyPDF2: {e}")
        
        return pages_data
    
    def convert_to_images(self, pdf_path: str, output_dir: str, on_progress=None) -> List[str]:
        """Convert PDF pages to images."""
        image_paths = []
        
        try:
            print("Converting PDF pages to images...")
            if on_progress:
                on_progress(32, "Rendering page images...", 0, 0)
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=150)  # 150 DPI for good quality
            
            os.makedirs(output_dir, exist_ok=True)
            total = len(images)
            
            for i, image in enumerate(images, 1):
                image_filename = f"page_{i:03d}.png"
                image_path = os.path.join(output_dir, image_filename)
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
                print(f"Saved page {i} as {image_path}")
                if on_progress and total:
                    percent = 32 + int(20 * i / total)
                    on_progress(
                        percent,
                        f"Saving page image {i} of {total}",
                        i,
                        total,
                    )
        
        except Exception as e:
            print(f"Error converting to images: {e}")
            print("Note: You may need to install poppler-utils: sudo apt install poppler-utils")
        
        return image_paths
    
    def parse_pdf(self, pdf_path: str, output_dir: str = "alternative_output", on_progress=None) -> Dict:
        """
        Parse PDF using multiple methods for maximum compatibility.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"🚀 Parsing PDF: {pdf_path}")
        print("=" * 60)
        
        # Method 1: pdfplumber (best for text)
        print("📝 Extracting text with pdfplumber...")
        pdfplumber_data = self.extract_text_pdfplumber(pdf_path, on_progress=on_progress)
        
        # Method 2: PyPDF2 (fallback)
        print("\n📝 Extracting text with PyPDF2 (fallback)...")
        if on_progress:
            on_progress(30, "Checking leftover pages...", 0, 0)
        pypdf2_data = self.extract_text_pypdf2(pdf_path)
        
        # Method 3: Convert to images
        print("\n🖼️ Converting pages to images...")
        image_paths = self.convert_to_images(pdf_path, output_dir, on_progress=on_progress)
        
        # Combine results - prefer pdfplumber data
        final_pages = []
        page_count = max(len(pdfplumber_data), len(pypdf2_data), len(image_paths))
        
        for i in range(page_count):
            page_num = i + 1
            
            # Start with pdfplumber data
            if i < len(pdfplumber_data):
                page_data = pdfplumber_data[i].copy()
            else:
                page_data = {'page_number': page_num, 'text': '', 'word_count': 0}
            
            # Add PyPDF2 data as fallback
            if i < len(pypdf2_data) and not page_data.get('text'):
                page_data['text'] = pypdf2_data[i].get('text', '')
                page_data['word_count'] = pypdf2_data[i].get('word_count', 0)
                page_data['extraction_method'] = 'PyPDF2'
            else:
                page_data['extraction_method'] = 'pdfplumber'
            
            # Add image path
            if i < len(image_paths):
                page_data['image_path'] = image_paths[i]
            
            final_pages.append(page_data)
        
        # Compile final results
        all_text = "\n\n".join([page.get('text', '') for page in final_pages])
        total_words = sum([page.get('word_count', 0) for page in final_pages])
        
        result = {
            'pdf_path': pdf_path,
            'page_count': page_count,
            'pages': final_pages,
            'total_text': all_text,
            'total_words': total_words,
            'output_directory': output_dir,
            'methods_used': ['pdfplumber', 'PyPDF2', 'pdf2image']
        }
        
        print(f"\n✅ Parsing completed!")
        print(f"📄 Pages: {page_count}")
        print(f"📝 Total words: {total_words}")
        print(f"📁 Output directory: {output_dir}")
        
        return result
    
    def save_results(self, results: Dict, output_file: str = "alternative_results.json"):
        """Save results to JSON file."""
        # Create clean version for JSON
        clean_results = results.copy()
        clean_results['pages'] = [
            {
                'page_number': page['page_number'],
                'text_preview': page.get('text', '')[:300] + '...' if len(page.get('text', '')) > 300 else page.get('text', ''),
                'word_count': page.get('word_count', 0),
                'image_path': page.get('image_path'),
                'extraction_method': page.get('extraction_method', 'unknown'),
                'width': page.get('width'),
                'height': page.get('height')
            }
            for page in results['pages']
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Results saved to: {output_file}")
        
        # Also save full text
        text_file = output_file.replace('.json', '.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(results['total_text'])
        print(f"📝 Full text saved to: {text_file}")


def main():
    """Test the alternative parser."""
    parser = AlternativePDFParser()
    pdf_file = "sample1.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file '{pdf_file}' not found!")
        return
    
    try:
        # Parse the PDF
        results = parser.parse_pdf(pdf_file)
        
        # Save results
        parser.save_results(results)
        
        # Show summary
        print("\n" + "=" * 60)
        print("📊 PARSING SUMMARY")
        print("=" * 60)
        print(f"File: {results['pdf_path']}")
        print(f"Pages: {results['page_count']}")
        print(f"Total words: {results['total_words']}")
        print(f"Methods used: {', '.join(results['methods_used'])}")
        
        # Show first page preview
        if results['pages']:
            first_page = results['pages'][0]
            preview = first_page.get('text', '')[:200]
            print(f"\n📖 First page preview:")
            print(f"Method: {first_page.get('extraction_method', 'unknown')}")
            print(f"Text: {preview}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 