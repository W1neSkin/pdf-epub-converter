# PDF to EPUB Converter

[![Deploy React App to GitHub Pages](https://github.com/W1neSkin/pdf-epub-converter/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/W1neSkin/pdf-epub-converter/actions/workflows/deploy-pages.yml)

Open-source web application for converting PDF documents into fixed-layout EPUB books, readable Excel workbooks and table-only CSV files.

The EPUB output preserves every PDF page as an image and adds a precisely positioned, selectable text layer. The spreadsheet workflow extracts document content into XLSX and exports detected tables as combined or separate CSV files.

**Live application:** https://w1neskin.github.io/pdf-epub-converter/

## Output formats

### EPUB book

- Fixed-layout EPUB 3 output
- Original PDF page appearance
- Selectable and copyable text
- Precise selection inside table cells
- Built-in responsive EPUB reader
- Personal EPUB library

### Excel and table files

- Readable XLSX workbook with one worksheet per PDF page
- Text and detected tables in the same workbook
- Combined CSV containing all detected tables
- ZIP archive with one CSV file per table
- OCR fallback for scanned documents

## Main features

- Local PDF preview before conversion starts
- Drag-and-drop and standard file selection
- PDF metadata, page count and size validation
- Two clear workflows: EPUB or Excel with tables
- `pdfplumber`, Camelot and Tesseract OCR table extraction
- Fixed-layout page images generated with Poppler
- Invisible text overlay with character coordinates
- Authentication with JWT and Supabase
- Cloudinary storage for saved EPUB books
- Searchable library with list and grid views
- Desktop and mobile responsive interface

## How to use

1. Open the [online converter](https://w1neskin.github.io/pdf-epub-converter/).
2. Create a free account or sign in.
3. Upload a PDF and review it in the browser.
4. Choose **EPUB book** or **Excel + tables**.
5. Start conversion and wait for processing.
6. Download the result or open the EPUB in the built-in reader.

The current free service accepts PDF files up to **50 MB** and **50 pages**.

## Technology

### Frontend

- React 19
- styled-components
- pdf-lib
- JSZip
- GitHub Pages

### Backend

- Python and FastAPI
- pdfplumber and PyPDF2
- pdf2image and Poppler
- Camelot
- Tesseract OCR
- openpyxl
- Railway

### Data and storage

- Supabase authentication and database
- Cloudinary EPUB storage
- JWT service authentication

## Architecture

```text
React frontend on GitHub Pages
             |
             v
API Gateway
   |         |         |
   v         v         v
Auth      Converter   Library
   |         |         |
   +---- Supabase -----+
             |
         Cloudinary
```

The converter renders PDF pages, extracts positioned text, creates fixed-layout XHTML and packages the result as EPUB 3. The table workflow orders extracted text and tables before generating XLSX, CSV and ZIP outputs.

## Local development

Clone the repository:

```bash
git clone https://github.com/W1neSkin/pdf-epub-converter.git
cd pdf-epub-converter
```

Start the React frontend:

```bash
cd frontend
npm install
npm start
```

For the complete microservices environment, configure the required Supabase, Cloudinary and JWT variables, then run:

```bash
docker compose -f docker-compose.microservices.yml up --build
```

See [environment setup](docs/environment-setup.md) and the [microservices guide](docs/MICROSERVICES_SETUP.md) for configuration details.

## Testing

Frontend:

```bash
cd frontend
npm test -- --watchAll=false
npm run build
```

Backend:

```bash
python -m pytest tests
```

## Documentation

- [Features](https://w1neskin.github.io/pdf-epub-converter/features.html)
- [How to use](https://w1neskin.github.io/pdf-epub-converter/how-to.html)
- [API documentation](docs/api-docs.md)
- [Environment setup](docs/environment-setup.md)
- [Microservices setup](docs/MICROSERVICES_SETUP.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Privacy](https://w1neskin.github.io/pdf-epub-converter/privacy.html)

## Contributing

Bug reports, feature requests, documentation improvements and pull requests are welcome through [GitHub Issues](https://github.com/W1neSkin/pdf-epub-converter/issues).
