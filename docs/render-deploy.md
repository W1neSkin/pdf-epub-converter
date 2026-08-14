# 🚀 Render Deployment Guide - Microservices Architecture

## 📋 Prerequisites

1. ✅ **Supabase project created** (follow `setup_supabase.md`)
2. ✅ **Environment variables configured** (see `.env.template`)
3. ✅ **Database schema created** in Supabase
4. ✅ **Code committed and pushed** to GitHub
5. ✅ **Render account created** at [render.com](https://render.com)

## 🏗️ Architecture Overview

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

## 🚀 Deploy Services in Order

**⚠️ Important**: Deploy services in this exact order due to dependencies.

### 1. Deploy Auth Service 🔐

1. **Go to [render.com](https://render.com)**
2. **Click "New +" → "Web Service"**
3. **Connect GitHub** repository: `W1neSkin/pdf-epub-converter`
4. **Service Configuration**:
   ```
   Name: pdf-converter-auth-service
   Environment: Docker
   Region: Oregon (or closest to you)
   Branch: master
   Root Directory: (leave empty)
   Dockerfile Path: services/auth-service/Dockerfile
   Docker Context: . (repository root)
   ```

5. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key-here
   JWT_SECRET=your-jwt-secret-here
   PORT=8001
   DEBUG=false
   LOG_LEVEL=INFO
   ```

6. **Advanced Settings**:
   - Auto-Deploy: Yes
   - Build Filter: `services/auth-service/**` or `shared/**`

7. **Click "Create Web Service"**
8. **Wait for deployment** (~5-10 minutes)
9. **Save service URL**: `https://pdf-converter-auth-service.onrender.com`

**✅ Test**: Visit `https://your-auth-service.onrender.com/health`

### 2. Deploy Library Service 📚

1. **Create new Web Service**
2. **Service Configuration**:
   ```
   Name: pdf-converter-library-service
   Environment: Docker
   Branch: master
   Dockerfile Path: services/library-service/Dockerfile
   Docker Context: . (repository root)
   ```

3. **Environment Variables**:
   ```
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key-here
   CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
   JWT_SECRET=your-jwt-secret-here
   PORT=8002
   DEBUG=false
   LOG_LEVEL=INFO
   ```

4. **Advanced Settings**:
   - Auto-Deploy: Yes
   - Build Filter: `services/library-service/**` or `shared/**`

5. **Deploy and save URL**: `https://pdf-converter-library-service.onrender.com`

**✅ Test**: Visit `https://your-library-service.onrender.com/health`

### 3. Deploy API Gateway 🌐

1. **Create new Web Service**
2. **Service Configuration**:
   ```
   Name: pdf-converter-api-gateway
   Environment: Docker
   Dockerfile Path: services/api-gateway/Dockerfile
   Docker Context: . (repository root)
   ```

3. **Environment Variables**:
   ```
   JWT_SECRET=your-jwt-secret-here
   AUTH_SERVICE_URL=https://pdf-converter-auth-service.onrender.com
   CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
   LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com
   PORT=8080
   DEBUG=false
   LOG_LEVEL=INFO
   ```

4. **Advanced Settings**:
   - Auto-Deploy: Yes
   - Build Filter: `services/api-gateway/**` or `shared/**`

5. **Deploy and save URL**: `https://pdf-converter-api-gateway.onrender.com`

**✅ Test**: Visit `https://your-api-gateway.onrender.com/health`

### 4. Update Existing Converter Service 🔄

1. **Go to your existing service**: `pdf-epub-converter-api`
2. **Environment** → **Add Environment Variables**:
   ```
   LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com
   JWT_SECRET=your-jwt-secret-here
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key-here
   ```
3. **Manual Deploy** to restart with new environment variables

**✅ Test**: Upload a PDF to verify library integration works

## 🧪 Test Deployment

### Service Health Checks
```bash
# Test Auth Service
curl https://pdf-converter-auth-service.onrender.com/health

# Test Library Service  
curl https://pdf-converter-library-service.onrender.com/health

# Test API Gateway
curl https://pdf-converter-api-gateway.onrender.com/health

# Test Converter Service
curl https://pdf-epub-converter-api.onrender.com/
```

### Authentication Flow
```bash
# Test registration through API Gateway
curl -X POST https://pdf-converter-api-gateway.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Test login
curl -X POST https://pdf-converter-api-gateway.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Save the token from login response for next tests
```

### Library Features (Authenticated)
```bash
# Get user's library (requires JWT token in Authorization header)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://pdf-converter-api-gateway.onrender.com/library/books

# Get library statistics
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://pdf-converter-api-gateway.onrender.com/library/stats
```

## 🖥️ Update Frontend

### Option A: Use API Gateway (Recommended)
1. **Edit** frontend configuration to use API Gateway
2. **Update API_BASE_URL**:
   ```javascript
   const API_BASE_URL = 'https://pdf-converter-api-gateway.onrender.com';
   ```
3. **Add authentication support** (see Phase 3 documentation)

### Option B: Keep Direct Converter Access
- Leave frontend as-is for anonymous conversions
- API Gateway provides additional features for authenticated users

## 🔧 Troubleshooting

### ⚠️ **FIXED COMMON ISSUES** ⚠️

#### **✅ Dependency Resolution (SOLVED)**
```bash
# Use these EXACT versions in requirements.txt:
httpx==0.24.1               # NOT 0.25.2 (conflicts with supabase)
supabase==2.0.2            # Standardized across services
pydantic==2.5.0            # With v2 compatibility fixes
pydantic-settings==2.1.0   # Required for BaseSettings
email-validator==2.1.0     # Explicit dependency for EmailStr
```

#### **✅ Pydantic v2 Migration (SOLVED)**
```python
# Import fix
from pydantic_settings import BaseSettings  # NOT from pydantic

# Field validation fix
pattern="^(asc|desc)$"  # NOT regex="^(asc|desc)$"
```

#### **✅ Docker Configuration (SOLVED)**
```dockerfile
FROM python:3.11-slim  # NOT 3.12-slim (better compatibility)
```

#### **✅ Render Service Setup (SOLVED)**
```
Dockerfile Path: services/auth-service/Dockerfile
Docker Context: . (repository root)
Build Filter: services/auth-service/** or shared/**
```

### **Remaining Common Issues:**

1. **Service Status "degraded"**: 
   - ✅ Add ALL environment variables (see environment-setup.md)
   - ✅ Verify Supabase URL and Service Key format
   - ✅ Check JWT_SECRET is identical across services

2. **Inter-service communication fails**: 
   - ✅ Update service URLs in API Gateway environment
   - ✅ Ensure all services are deployed and running
   - ✅ Test individual service health endpoints

3. **Frontend connection issues**:
   - ✅ Update API_BASE_URL to use API Gateway
   - ✅ Deploy frontend with updated configuration
   - ✅ Check CORS settings in gateway

### **Need Help?**
📖 **See complete troubleshooting guide**: [troubleshooting.md](./troubleshooting.md)

### Debug Steps:

1. **Check Service Logs**:
   - Go to service in Render dashboard
   - Click **"Logs"** tab
   - Look for startup errors or runtime issues

2. **Test Service Health**:
   ```bash
   curl https://your-service.onrender.com/health
   ```

3. **Verify Environment Variables**:
   - Check each service has required variables
   - Verify secrets are not exposed in logs

4. **Database Debugging**:
   - Test Supabase connection in dashboard
   - Check RLS policies are allowing operations
   - Verify user registration creates profile

### Performance Notes:
- **Free Tier**: Services sleep after 15 minutes of inactivity
- **Wake Time**: 30-60 seconds for first request after sleep
- **Monthly Limits**: 750 hours per service on free tier
- **Scaling**: Automatic within resource limits

---

## 🎯 **Final Architecture**

```
Frontend (GitHub Pages)
         ↓
API Gateway (Render) ← Main Entry Point
    ↓     ↓     ↓
Auth   Conv   Library
Service ice   Service
    ↓     ↓     ↓
    Supabase (Database + Auth + Storage)
         +
    Cloudinary (File Storage)
```

### 📊 **Service URLs** (Update with your actual URLs):
- **API Gateway**: `https://pdf-converter-api-gateway.onrender.com`
- **Auth Service**: `https://pdf-converter-auth-service.onrender.com`
- **Library Service**: `https://pdf-converter-library-service.onrender.com`
- **Converter Service**: `https://pdf-epub-converter-api.onrender.com`

### 🔄 **Request Flow**:
1. Frontend → API Gateway
2. API Gateway → Auth Service (for login/register)
3. API Gateway → Converter Service (for PDF conversion)
4. API Gateway → Library Service (for book management)
5. Services → Supabase/Cloudinary for data/file storage

**All communication goes through the gateway for security and routing! 🎉** 