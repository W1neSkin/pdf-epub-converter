# PDF to EPUB Converter

[![Deploy React App to GitHub Pages](https://github.com/W1neSkin/pdf-epub-converter/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/W1neSkin/pdf-epub-converter/actions/workflows/deploy-pages.yml)

Web application that turns a PDF into a fixed-layout EPUB, an Excel workbook, and CSV files for the tables it finds.

Text and scans are converted with [PDFCalque](https://github.com/W1neSkin/PDFCalque). PDFCalque reads the PDF itself: real letters, positions, embedded fonts, and the bookmark tree. A scan stays the picture already stored in the file. Pages that are mostly vector drawings still go through Poppler, because PDFCalque does not paint shadings and blends. If the PDFCalque program is missing, the older Poppler pipeline is used for the whole EPUB.

Tables are extracted twice. PDFCalque looks for a drawn grid and for short words lined up in columns. pdfplumber, Camelot, and Tesseract look as well. Each page keeps the result with the better cells. Long prose in two columns is not stored as a table. A scan that has no text layer can still reach the Tesseract fallback.

**Live application:** https://w1neskin.github.io/pdf-epub-converter/

## Output formats

### EPUB book

- Fixed-layout EPUB 3
- Text, fonts, and pictures taken from the PDF when PDFCalque handles the file
- Bookmark tree as the table of contents, including the place on the page
- Original scan image when the page has no text layer
- Poppler page image for vector-only artwork
- Built-in reader that shows the page, the embedded fonts, and the outline
- Personal EPUB library

### Excel and table files

- Readable XLSX workbook with one worksheet per PDF page
- Text and detected tables in the same workbook
- Combined CSV containing all detected tables
- ZIP archive with one CSV file per table
- OCR fallback for scanned pages that have no text layer

## Main features

- Local PDF preview before conversion starts
- Drag-and-drop and standard file selection
- PDF metadata, page count, and size validation
- Two workflows: EPUB, or Excel with tables
- PDFCalque for text, fonts, scans, and aligned tables
- pdfplumber, Camelot, and Tesseract when they produce the better table
- Authentication with JWT and Supabase
- Cloudinary storage for saved EPUB books
- Searchable library with list and grid views
- Desktop and mobile layout

## How to use

1. Open the [online converter](https://w1neskin.github.io/pdf-epub-converter/).
2. Create a free account or sign in.
3. Upload a PDF and review it in the browser.
4. Choose **EPUB book** or **Excel + tables**.
5. Start conversion and wait for processing.
6. Download the result or open the EPUB in the built-in reader.

The free service accepts PDF files up to **50 MB** and **50 pages**.

## Technology

### Frontend

- React 19
- styled-components
- pdf-lib
- JSZip
- GitHub Pages

### Backend

- Python and FastAPI
- PDFCalque, the Rust library in `backend/pdfcalque`
- pdfplumber and PyPDF2
- pdf2image and Poppler, used when PDFCalque is not the better page
- Camelot and Tesseract OCR for tables
- openpyxl
- Render

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

The converter calls `pdfcalque export` for an EPUB and `pdfcalque tables` when it is scoring tables. The report says how much text, how many full-page images, and how many paths the PDF contains. That report chooses PDFCalque or Poppler for the book. Table rows from both engines are scored, and the stronger cells are written to Excel and CSV.

Deploy compiles PDFCalque from `backend/pdfcalque` (`backend/build.sh`, or the Dockerfiles). The program is also found in `PDFCALQUE_BIN`, on `PATH`, or in a sibling `PDFCalque/target/release` checkout.

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

For the complete microservices environment, configure the required Supabase, Cloudinary, and JWT variables, then run:

```bash
docker compose -f docker-compose.microservices.yml up --build
```

The image build compiles PDFCalque. To point the Python process at a binary you built yourself, build it in the PDFCalque repo and set `PDFCALQUE_BIN` to that program:

```bash
cargo build --release --bin pdfcalque
export PDFCALQUE_BIN=/path/to/pdfcalque
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

Bug reports, feature requests, documentation improvements, and pull requests are welcome through [GitHub Issues](https://github.com/W1neSkin/pdf-epub-converter/issues).
