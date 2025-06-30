# PDF to EPUB Converter

A comprehensive PDF to EPUB conversion system with a modern React frontend and **microservices architecture**. Converts PDFs to interactive EPUB files with selectable text overlays that maintain the visual appearance of the original PDF while providing full text selection and copying capabilities.

## 🌐 Live Demo
**Try it now:** https://w1neskin.github.io/pdf-epub-converter

Upload an EPUB file and experience the interactive text selection features!

## 📚 **Complete Documentation**
**🎯 [All documentation now available in `docs/` folder](./docs/)**

- **🚀 [Deployment Guide](./docs/render-deploy.md)** - Deploy to Render with all fixes included
- **🔧 [Environment Setup](./docs/environment-setup.md)** - Complete configuration guide  
- **🆘 [Troubleshooting](./docs/troubleshooting.md)** - All common issues and solutions
- **📖 [API Documentation](./docs/api-docs.md)** - Complete API reference
- **🏗️ [Architecture Guide](./docs/MICROSERVICES_SETUP.md)** - Microservices setup

## 🏢 **Microservices Architecture**

```
Frontend (GitHub Pages)
         ↓
API Gateway (Render)
    ↓     ↓     ↓
Auth   Conv   Library
Service ice   Service
    ↓     ↓     ↓
    Supabase + Cloudinary
```

**Live Services:**
- **API Gateway**: `https://pdf-converter-api-gateway.onrender.com`
- **Auth Service**: User registration, login, JWT tokens
- **Library Service**: Personal book management, storage tracking
- **Converter Service**: PDF to EPUB processing

## 🌟 Features

### 🔄 PDF Processing Engine
- **Multiple extraction methods**: Uses `pdfplumber`, `PyPDF2`, and `pdf2image` for robust PDF processing
- **High-quality image conversion**: Generates crisp PNG images from PDF pages
- **Precise text extraction**: Extracts text with accurate positioning data
- **Responsive positioning**: Percentage-based coordinates that scale perfectly

### 📚 EPUB Generation
- **EPUB 3.0 format**: Standards-compliant EPUB files
- **Interactive text layers**: Invisible text overlays for perfect selection
- **Professional appearance**: Clean, PDF-like reading experience
- **Cross-platform compatibility**: Works with Kindle, Apple Books, Adobe Digital Editions

### 🖱️ Text Selection Features
- **Visual selection**: Click and drag to select text on PDF images
- **Multi-word selection**: Drag across multiple words and lines
- **Keyboard shortcuts**: Ctrl+C to copy, Ctrl+A to select all, Escape to clear
- **Invisible text layer**: Professional appearance with full functionality

### 🎨 React Frontend
- **Modern UI**: Beautiful, responsive interface with gradient design
- **User Management**: Complete authentication system with login/registration
- **Personal Library**: Save and manage your converted books with statistics
- **User Dashboard**: Centralized view of conversions, storage usage, and account
- **Secure Access**: All operations require user authentication for security
- **Drag & drop**: Easy EPUB file uploading
- **Real-time rendering**: Instant EPUB viewing and navigation
- **Mobile responsive**: Works perfectly on all devices

## 🚀 Quick Start

### **🌟 Production (Microservices)**
**✅ Ready to use - No setup required!**

**🔐 Authentication Required:**
1. **Visit**: https://w1neskin.github.io/pdf-epub-converter
2. **Sign Up/Login**: Create an account or log in to access all features
3. **Dashboard**: Access your personal library and conversion statistics
4. **Convert PDFs**: Upload and convert with automatic library saving
5. **Read EPUBs**: Upload EPUB files to read with full functionality
6. **Manage**: Download, organize, and delete your converted books

**📖 [Complete deployment guide](./docs/render-deploy.md)** to deploy your own instance.

### **💻 Local Development**

```bash
# Clone the repository
git clone https://github.com/W1neSkin/pdf-epub-converter.git
cd pdf-epub-converter

# Quick start with Docker
docker-compose up -d

# OR microservices development  
docker-compose -f docker-compose.microservices.yml up

# Access the application
# Frontend: http://localhost:3000
# Backend: Available for processing
```

**📖 [See complete setup guide](./docs/MICROSERVICES_SETUP.md)** for detailed local development instructions.

### Manual Setup

1. **Backend Setup**:
```bash
cd backend
python3 -m venv pdf_parser_env
source pdf_parser_env/bin/activate
pip install -r requirements.txt
```

2. **Frontend Setup**:
```bash
cd frontend
npm install
npm start
```

## 📖 Usage

### 1. PDF to EPUB Conversion

```bash
# Navigate to backend directory
cd backend

# Convert PDF to images and extract text
python3 alternative_parser.py

# Generate interactive HTML pages
python3 html_generator.py

# Create EPUB file
python3 epub_generator.py
```

### 2. Using the React Frontend

1. Open http://localhost:3000
2. Upload an EPUB file using the drag & drop interface
3. Navigate through pages using arrow keys or navigation controls
4. Select text by clicking and dragging on the PDF images
5. Copy selected text with Ctrl+C

## 🏗️ Architecture

```
pdf-epub-converter/
├── backend/                    # Python processing engine
│   ├── alternative_parser.py   # PDF text & image extraction
│   ├── html_generator.py      # Interactive HTML generation
│   ├── epub_generator.py      # EPUB file creation
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Backend container
├── frontend/                  # React EPUB reader
│   ├── src/components/       # React components
│   ├── package.json          # Node.js dependencies
│   └── Dockerfile           # Frontend container
├── docker-compose.yml        # Production deployment
├── docker-compose.dev.yml    # Development setup
└── README.md                 # This file
```

## 🔧 Technical Details

### PDF Processing Pipeline

1. **Text Extraction**: Uses `pdfplumber` for precise text positioning and `PyPDF2` as fallback
2. **Image Generation**: Converts PDF pages to high-resolution PNG images with `pdf2image`
3. **Coordinate Mapping**: Transforms PDF coordinates to web-compatible percentage-based positioning
4. **HTML Generation**: Creates responsive HTML pages with invisible text overlays
5. **EPUB Assembly**: Packages HTML, images, and metadata into EPUB 3.0 format

### Text Selection Technology

- **Invisible Overlays**: Text elements are completely transparent but fully interactive
- **Responsive Design**: Uses percentage-based positioning that scales with any screen size
- **Professional Appearance**: Maintains clean PDF-like visual experience
- **Perfect Alignment**: Text overlays precisely match the visual text in images

### React EPUB Reader

- **JSZip Integration**: Extracts and processes EPUB files in the browser
- **Dynamic Rendering**: Real-time HTML content processing and display
- **Keyboard Navigation**: Arrow key support for page navigation
- **Mobile Optimization**: Touch-friendly interface for tablets and phones

## 🐳 Docker Configuration

### Production Deployment
```bash
docker-compose up -d
```

### Development Mode
```bash
docker-compose -f docker-compose.dev.yml up
```

### Services
- **Frontend**: React app served on port 3000
- **Backend**: Python processing environment with all dependencies
- **Network**: Custom bridge network for service communication

## 📋 Requirements

### System Requirements
- Docker and Docker Compose (recommended)
- OR Python 3.8+ and Node.js 16+
- 2GB+ RAM for processing large PDFs
- `poppler-utils` for PDF processing (included in Docker)

### Python Dependencies
```
pdfplumber==0.11.7
PyPDF2==3.0.1
pdf2image==1.17.0
Pillow==10.1.0
beautifulsoup4==4.12.2
lxml==4.9.4
```

### Node.js Dependencies
```
react==18.2.0
styled-components==6.1.8
jszip==3.10.1
```

## 🎯 Features in Detail

### ✅ What Works
- ✅ PDF to PNG image conversion
- ✅ Accurate text extraction with positioning
- ✅ Responsive HTML page generation
- ✅ EPUB 3.0 file creation
- ✅ React-based EPUB reader
- ✅ Invisible text layer with perfect selection
- ✅ Keyboard shortcuts and navigation
- ✅ Mobile-responsive design
- ✅ Docker containerization

### 🚀 Future Enhancements
- 🔄 Batch PDF processing
- 🔄 OCR support for scanned PDFs
- 🔄 Advanced text formatting preservation
- 🔄 Annotation and highlighting features
- 🔄 Multi-language support

## 🛠️ Development

### Adding New Features

1. **Backend changes**: Modify Python files in `backend/`
2. **Frontend changes**: Edit React components in `frontend/src/`
3. **Rebuild containers**: `docker-compose build`
4. **Test changes**: `docker-compose up -d`

### Debugging

```bash
# View container logs
docker-compose logs frontend
docker-compose logs backend

# Access container shell
docker exec -it pdf-epub-backend bash
docker exec -it pdf-epub-frontend sh
```

## 📄 License

This project is open source. Feel free to use, modify, and distribute as needed.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit:

- 🐛 Bug reports
- 💡 Feature requests
- 🔧 Pull requests
- 📚 Documentation improvements

## 📞 Support

If you encounter any issues or have questions:

1. Check the troubleshooting section
2. Review Docker logs for error messages
3. Ensure all dependencies are properly installed
4. Verify PDF files are not corrupted or password-protected

---

**Built with ❤️ using Python, React, and Docker** 