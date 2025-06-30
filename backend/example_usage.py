#!/usr/bin/env python3
"""
Example usage of the PDF parsers.
This script demonstrates both basic and advanced parsing capabilities.
"""

import os
import sys
import argparse
from pdf_parser import PDFParser
from advanced_parser import AdvancedPDFParser


def demo_basic_parser(pdf_path: str, output_dir: str = "basic_output"):
    """Demonstrate basic PDF parser functionality."""
    print("=" * 60)
    print("BASIC PDF PARSER DEMO")
    print("=" * 60)
    
    parser = PDFParser(headless=True)
    
    try:
        print(f"Parsing: {pdf_path}")
        results = parser.parse_pdf(pdf_path, output_dir)
        
        # Save results
        parser.save_results(results, os.path.join(output_dir, "results.json"))
        
        # Display summary
        print(f"\n📄 PDF Summary:")
        print(f"   File: {results['pdf_path']}")
        print(f"   Pages: {results['page_count']}")
        print(f"   Total text length: {len(results['total_text'])} characters")
        print(f"   Output directory: {results['output_directory']}")
        
        # Show first page preview
        if results['pages']:
            first_page = results['pages'][0]
            preview = first_page['text'][:200] + "..." if len(first_page['text']) > 200 else first_page['text']
            print(f"\n📝 First page preview:")
            print(f"   {preview}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in basic parser: {e}")
        return None


def demo_advanced_parser(pdf_path: str, output_dir: str = "advanced_output"):
    """Demonstrate advanced PDF parser functionality."""
    print("\n" + "=" * 60)
    print("ADVANCED PDF PARSER DEMO")
    print("=" * 60)
    
    parser = AdvancedPDFParser(headless=True, log_level="INFO")
    
    try:
        print(f"Parsing: {pdf_path}")
        results = parser.parse_pdf_advanced(pdf_path, output_dir)
        
        # Export to multiple formats
        parser.export_to_formats(results, "advanced_results")
        
        # Display detailed summary
        print(f"\n📄 Advanced PDF Summary:")
        print(f"   File: {results['pdf_path']}")
        print(f"   Pages: {results['page_count']}")
        print(f"   Total words: {results['total_words']}")
        print(f"   Output directory: {results['output_directory']}")
        
        # Show text element statistics
        if results['pages']:
            total_elements = sum(len(page.text_elements) for page in results['pages'])
            avg_elements_per_page = total_elements / len(results['pages'])
            print(f"   Text elements: {total_elements} total ({avg_elements_per_page:.1f} per page)")
            
            # Show sample text elements from first page
            first_page = results['pages'][0]
            if first_page.text_elements:
                print(f"\n🔍 Sample text elements from page 1:")
                for i, elem in enumerate(first_page.text_elements[:3]):
                    print(f"   Element {i+1}: '{elem.text[:30]}...' at ({elem.x:.1f}, {elem.y:.1f})")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in advanced parser: {e}")
        return None


def compare_parsers(pdf_path: str):
    """Compare results from both parsers."""
    print("\n" + "=" * 60)
    print("PARSER COMPARISON")
    print("=" * 60)
    
    basic_results = demo_basic_parser(pdf_path, "comparison_basic")
    advanced_results = demo_advanced_parser(pdf_path, "comparison_advanced")
    
    if basic_results and advanced_results:
        print(f"\n📊 Comparison Results:")
        print(f"   Basic parser - Text length: {len(basic_results['total_text'])} chars")
        print(f"   Advanced parser - Text length: {len(advanced_results['total_text'])} chars")
        print(f"   Advanced parser - Word count: {advanced_results['total_words']} words")
        
        # Calculate text extraction accuracy
        basic_words = len(basic_results['total_text'].split())
        advanced_words = advanced_results['total_words']
        if basic_words > 0:
            accuracy_ratio = advanced_words / basic_words
            print(f"   Word extraction ratio (advanced/basic): {accuracy_ratio:.2f}")


def create_sample_html_report(results, output_path: str = "report.html"):
    """Create a simple HTML report from parsing results."""
    if not results:
        return
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Parsing Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .page {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            .screenshot {{ max-width: 300px; float: right; margin-left: 20px; }}
            .text-content {{ text-align: justify; }}
            .stats {{ background-color: #e8f4fd; padding: 10px; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>PDF Parsing Report</h1>
            <div class="stats">
                <strong>File:</strong> {results['pdf_path']}<br>
                <strong>Pages:</strong> {results['page_count']}<br>
                <strong>Total Words:</strong> {results.get('total_words', 'N/A')}<br>
                <strong>Output Directory:</strong> {results['output_directory']}
            </div>
        </div>
    """
    
    # Add pages
    pages = results.get('pages', [])
    for i, page in enumerate(pages):
        page_num = getattr(page, 'page_number', i + 1)
        page_text = getattr(page, 'full_text', page.get('text', ''))
        screenshot_path = getattr(page, 'screenshot_path', page.get('screenshot_path'))
        
        html_content += f"""
        <div class="page">
            <h3>Page {page_num}</h3>
        """
        
        if screenshot_path and os.path.exists(screenshot_path):
            html_content += f'<img src="{os.path.basename(screenshot_path)}" class="screenshot" alt="Page {page_num} screenshot">'
        
        html_content += f"""
            <div class="text-content">
                <p>{page_text[:500] + '...' if len(page_text) > 500 else page_text}</p>
            </div>
            <div style="clear: both;"></div>
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📄 HTML report created: {output_path}")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="PDF Parser Demo")
    parser.add_argument("pdf_path", nargs="?", help="Path to PDF file")
    parser.add_argument("--mode", choices=["basic", "advanced", "compare"], 
                       default="compare", help="Parser mode to use")
    parser.add_argument("--output", default="demo_output", help="Output directory")
    parser.add_argument("--report", action="store_true", help="Generate HTML report")
    
    args = parser.parse_args()
    
    # Check for PDF file
    if not args.pdf_path:
        # Look for any PDF file in current directory
        pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
        if pdf_files:
            args.pdf_path = pdf_files[0]
            print(f"📁 Found PDF file: {args.pdf_path}")
        else:
            print("❌ No PDF file specified and none found in current directory.")
            print("Usage: python example_usage.py <pdf_file> [options]")
            print("\nTo test the parser, you can:")
            print("1. Download a sample PDF file")
            print("2. Place it in the current directory")
            print("3. Run: python example_usage.py sample.pdf")
            return
    
    if not os.path.exists(args.pdf_path):
        print(f"❌ PDF file not found: {args.pdf_path}")
        return
    
    print(f"🚀 Starting PDF parsing demo with {args.pdf_path}")
    
    # Run selected mode
    results = None
    if args.mode == "basic":
        results = demo_basic_parser(args.pdf_path, args.output)
    elif args.mode == "advanced":
        results = demo_advanced_parser(args.pdf_path, args.output)
    elif args.mode == "compare":
        compare_parsers(args.pdf_path)
        # Use advanced results for report
        results = demo_advanced_parser(args.pdf_path, args.output)
    
    # Generate HTML report if requested
    if args.report and results:
        report_path = os.path.join(args.output, "report.html")
        create_sample_html_report(results, report_path)
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    main() 