# 🔧 Environment Configuration Guide

Complete guide for setting up environment variables and configuration for the PDF to EPUB Converter microservices.

## 📋 **Required Environment Variables**

### **🔐 Auth Service Environment**

```bash
# Service Configuration
SERVICE_NAME=auth-service
PORT=8001
DEBUG=false
LOG_LEVEL=INFO

# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJ...your-service-key...

# JWT Configuration  
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Settings
FRONTEND_URL=https://your-username.github.io/pdf-epub-converter
```

### **📚 Library Service Environment**

```bash
# Service Configuration
SERVICE_NAME=library-service
PORT=8002
DEBUG=false
LOG_LEVEL=INFO

# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJ...your-service-key...

# Cloudinary Configuration (for file storage)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# JWT Configuration
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013

# Library Limits (free tier)
MAX_BOOKS_PER_USER=50
MAX_STORAGE_PER_USER=1073741824  # 1GB
```

### **🌐 API Gateway Environment**

```bash
# Service Configuration
SERVICE_NAME=api-gateway
PORT=8080
DEBUG=false
LOG_LEVEL=INFO

# JWT Configuration
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013

# Service URLs (update with your actual URLs)
AUTH_SERVICE_URL=https://pdf-converter-auth-service.onrender.com
CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com

# Gateway Configuration
TIMEOUT=60
MAX_RETRIES=3

# CORS Settings
FRONTEND_URL=https://your-username.github.io/pdf-epub-converter
```

### **🔄 Converter Service Environment** (Existing Service Update)

```bash
# Add these to your existing converter service
LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJ...your-service-key...

# Processing Limits
PDF_TIMEOUT=300
MAX_PAGES=100
```

## 🗃️ **Getting Your Credentials**

### **Supabase Credentials**

1. **Go to** [supabase.com](https://supabase.com)
2. **Select your project**
3. **Go to Settings** → **API**
4. **Copy**:
   - `Project URL` → `SUPABASE_URL`
   - `service_role secret` → `SUPABASE_SERVICE_KEY`

### **Cloudinary Credentials** (Optional for file storage)

1. **Go to** [cloudinary.com](https://cloudinary.com)
2. **Dashboard** → **Account Details**
3. **Copy**:
   - `Cloud Name` → `CLOUDINARY_CLOUD_NAME`
   - `API Key` → `CLOUDINARY_API_KEY`
   - `API Secret` → `CLOUDINARY_API_SECRET`
   - Format `CLOUDINARY_URL`: `cloudinary://api_key:api_secret@cloud_name`

### **JWT Secret Key**

Use the provided key for consistency:
```bash
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
```

**⚠️ Important**: This key must be **IDENTICAL** across all services!

## 🚀 **Render Configuration**

### **Adding Environment Variables in Render**

1. **Go to** your service in Render Dashboard
2. **Click** "Environment" tab
3. **Click** "Add Environment Variable"
4. **Add each variable** with exact name and value
5. **Deploy** the service to apply changes

### **Service-Specific Instructions**

#### **Auth Service**
```
Service Name: pdf-converter-auth-service
Dockerfile Path: services/auth-service/Dockerfile
Docker Context: .
```

#### **Library Service**
```
Service Name: pdf-converter-library-service
Dockerfile Path: services/library-service/Dockerfile  
Docker Context: .
```

#### **API Gateway**
```
Service Name: pdf-converter-api-gateway
Dockerfile Path: services/api-gateway/Dockerfile
Docker Context: .
```

## 💻 **Local Development**

### **Using .env File**

Create `.env` in project root:
```bash
# Copy from env.template
cp env.template .env

# Edit with your values
nano .env
```

### **Docker Compose Setup**

```bash
# Development setup
docker-compose -f docker-compose.dev.yml up

# Microservices setup
docker-compose -f docker-compose.microservices.yml up
```

## 🧪 **Testing Configuration**

### **Verify Environment Variables**

```bash
# Test service health with configuration
curl https://pdf-converter-auth-service.onrender.com/health

# Expected response:
{
  "service_name": "auth-service",
  "status": "healthy",
  "database_connected": true,
  "dependencies": {"supabase": "connected"}
}
```

### **Common Configuration Issues**

#### **Database Connection Failed**
- ✅ Check SUPABASE_URL format (https://...)
- ✅ Verify SUPABASE_SERVICE_KEY is service_role (not anon)
- ✅ Ensure Supabase project is not paused

#### **JWT Token Issues**
- ✅ Ensure JWT_SECRET_KEY is identical across all services
- ✅ Verify no extra spaces or characters in the key
- ✅ Check JWT_ALGORITHM is "HS256"

#### **Inter-Service Communication**
- ✅ Verify service URLs are correct and accessible
- ✅ Check services are deployed and running
- ✅ Test individual service health endpoints

## 🔗 **Frontend Configuration**

### **Update API Base URL**

In `frontend/src/components/PdfUploader.js`:
```javascript
const API_BASE_URL = 'https://pdf-converter-api-gateway.onrender.com';
```

### **Deploy Frontend**

```bash
# GitHub Pages (automatic)
git push origin master

# Manual deploy
npm run build
npm run deploy
```

## 📊 **Environment Template**

Create `env.template` with placeholder values:
```bash
# Service Configuration
DEBUG=false
LOG_LEVEL=INFO

# Supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here

# JWT
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013

# Cloudinary (Optional)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# Service URLs (update after deployment)
AUTH_SERVICE_URL=https://pdf-converter-auth-service.onrender.com
CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com

# Frontend
FRONTEND_URL=https://your-username.github.io/pdf-epub-converter
```

---

**Security Notes:**
- ⚠️ Never commit actual credentials to git
- ✅ Use environment variables in all environments
- ✅ Rotate secrets regularly
- ✅ Use minimum required permissions

**Last Updated**: January 2025 