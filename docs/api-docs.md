# 📖 API Documentation

Complete API reference for the PDF to EPUB Converter microservices.

## 🌟 **Architecture Overview**

```
Frontend → API Gateway → [Auth | Converter | Library] Services → Database/Storage
```

**Base URL**: `https://pdf-converter-api-gateway.onrender.com`

## 🔐 **Authentication**

### **Register User**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}
```

### **Login User**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com", 
  "password": "password123"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user_id": "uuid"
  }
}
```

## 📄 **PDF Conversion**

### **Convert PDF to EPUB**
```http
POST /api/convert
Content-Type: multipart/form-data
Authorization: Bearer {token} (optional)

file: {pdf_file}
```

**Response**:
```json
{
  "success": true,
  "conversion_id": "uuid",
  "download_url": "https://...",
  "pages": 25,
  "total_words": 5000
}
```

### **Check Conversion Status**
```http
GET /api/status/{conversion_id}
Authorization: Bearer {token} (optional)
```

### **Download Converted File**
```http
GET /api/download/{file_id}
Authorization: Bearer {token} (optional)
```

## 📚 **Library Management** (Authenticated)

### **Get User's Books**
```http
GET /library/books?page=1&limit=20
Authorization: Bearer {token}
```

### **Get Book Details**
```http
GET /library/books/{book_id}
Authorization: Bearer {token}
```

### **Delete Book**
```http
DELETE /library/books/{book_id}
Authorization: Bearer {token}
```

### **Library Statistics**
```http
GET /library/stats
Authorization: Bearer {token}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "total_books": 15,
    "total_size": 52428800,
    "total_pages": 750,
    "total_words": 150000,
    "recent_conversions": 5,
    "storage_used_percent": 5.2
  }
}
```

## 🏥 **Health & Status**

### **API Gateway Health**
```http
GET /health
```

### **Service Health Checks**
```http
GET /auth/health      # Auth service
GET /library/health   # Library service  
GET /converter/health # Converter service
```

## 📊 **Response Formats**

### **Success Response**
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message",
  "timestamp": "2025-01-30T13:34:56Z"
}
```

### **Error Response**
```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid input provided",
  "details": { ... },
  "timestamp": "2025-01-30T13:34:56Z"
}
```

## 🔒 **Rate Limiting**

- **Free Tier**: 100 requests per minute
- **Authenticated**: Higher limits
- **File Size**: 50MB maximum per file

## 📝 **Error Codes**

| Code | Description |
|------|-------------|
| `INVALID_TOKEN` | JWT token invalid or expired |
| `FILE_TOO_LARGE` | File exceeds 50MB limit |
| `UNSUPPORTED_FORMAT` | File is not a valid PDF |
| `CONVERSION_FAILED` | PDF processing error |
| `STORAGE_LIMIT` | User storage quota exceeded |
| `RATE_LIMIT` | Too many requests |

## 🧪 **Testing**

### **Authentication Flow**
```bash
# Register
curl -X POST https://pdf-converter-api-gateway.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Login  
curl -X POST https://pdf-converter-api-gateway.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Use token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://pdf-converter-api-gateway.onrender.com/library/books
```

### **File Conversion**
```bash
# Convert PDF
curl -X POST https://pdf-converter-api-gateway.onrender.com/api/convert \
  -F "file=@document.pdf"
```

## 🔗 **SDKs & Integration**

### **JavaScript Frontend Integration**
```javascript
const API_BASE_URL = 'https://pdf-converter-api-gateway.onrender.com';

// Convert PDF
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch(`${API_BASE_URL}/api/convert`, {
  method: 'POST',
  body: formData,
  headers: {
    'Authorization': `Bearer ${token}` // Optional
  }
});

const result = await response.json();
```

---

**Interactive Documentation**: Visit `/docs` on the API Gateway for Swagger UI

**Last Updated**: January 2025 