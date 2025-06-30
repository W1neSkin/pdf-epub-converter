# 🔧 Troubleshooting Guide

Complete guide for resolving common deployment and runtime issues.

## 🚨 **Render Deployment Issues**

### **1. Dependency Resolution Errors**

#### **Problem**: `ResolutionImpossible: dependency conflicts`
```
ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/
```

#### **Solution**: Version Compatibility Fixes
```bash
# Update requirements.txt with compatible versions:
httpx==0.24.1          # (NOT 0.25.2 - conflicts with supabase)
supabase==2.0.2        # (standardized across all services)
pydantic==2.5.0        # (with proper v2 compatibility)
pydantic-settings==2.1.0  # (required for BaseSettings)
email-validator==2.1.0    # (explicit dependency for EmailStr)
```

### **2. Pydantic v2 Migration Issues**

#### **Problem**: `BaseSettings has been moved to pydantic-settings`
```python
pydantic.errors.PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package
```

#### **Solution**: Update Imports and Dependencies
```python
# OLD (Pydantic v1)
from pydantic import BaseSettings

# NEW (Pydantic v2)  
from pydantic_settings import BaseSettings
```

Add to requirements.txt:
```bash
pydantic-settings==2.1.0
```

#### **Problem**: `regex parameter removed`
```python
pydantic.errors.PydanticUserError: `regex` is removed. use `pattern` instead
```

#### **Solution**: Update Field Validation
```python
# OLD
sort_order: str = Field("desc", regex="^(asc|desc)$")

# NEW
sort_order: str = Field("desc", pattern="^(asc|desc)$")
```

#### **Problem**: `email-validator not installed`
```python
ImportError: email-validator is not installed, run `pip install pydantic[email]`
```

#### **Solution**: Explicit Email Validator
```bash
# Add to requirements.txt (pydantic[email] not sufficient in Docker)
email-validator==2.1.0
```

### **3. Docker Build Issues**

#### **Problem**: Dockerfile not found
```
error: failed to solve: failed to read dockerfile: open pdf-converter-api-gateway: no such file or directory
```

#### **Solution**: Correct Render Configuration
```
Dockerfile Path: services/auth-service/Dockerfile
Docker Context: . (repository root)
```

#### **Problem**: Python version compatibility
```
Collecting package... ERROR: No compatible distribution found
```

#### **Solution**: Use Stable Python Version
```dockerfile
# Change from
FROM python:3.12-slim

# To
FROM python:3.11-slim
```

## 🌐 **Service Health Issues**

### **Service Status: "degraded"**

#### **Problem**: Database connection failed
```json
{"status":"degraded","database_connected":false,"dependencies":{"supabase":"failed"}}
```

#### **Solution**: Add Environment Variables
```bash
# Required for all services
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here
JWT_SECRET_KEY=your-jwt-secret-here
```

### **Inter-Service Communication Issues**

#### **Problem**: Service dependencies unhealthy
```json
{"dependencies":{"auth":"healthy","converter":"unhealthy","library":"healthy"}}
```

#### **Solution**: Update Service URLs
```bash
# API Gateway environment variables
AUTH_SERVICE_URL=https://pdf-converter-auth-service.onrender.com
CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com  
LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com
```

## 📱 **Frontend Issues**

### **API Connection Problems**

#### **Problem**: CORS errors or 404s from frontend
```javascript
Failed to fetch: TypeError: NetworkError when attempting to fetch resource
```

#### **Solution**: Update API Base URL
```javascript
// Update in frontend/src/components/PdfUploader.js
const API_BASE_URL = 'https://pdf-converter-api-gateway.onrender.com';
```

### **Authentication Issues**

#### **Problem**: JWT token validation fails
```json
{"detail":"Invalid token"}
```

#### **Solution**: Ensure consistent JWT secret across all services
```bash
# Must be IDENTICAL across all services
JWT_SECRET_KEY=ffc42dc7409a15e7d29d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
```

## 🗄️ **Database Issues**

### **Supabase Connection Problems**

#### **Problem**: Connection string format
```
Database connection failed: invalid connection parameters
```

#### **Solution**: Correct Supabase configuration
```bash
# Format
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJ...your-service-key...
```

### **RLS Policy Issues**

#### **Problem**: Permission denied in database
```json
{"error":"permission denied for table users"}
```

#### **Solution**: Check Row Level Security policies in Supabase dashboard
- Ensure RLS policies allow service key access
- Verify user registration creates proper profile records

## 🚀 **Performance Issues**

### **Free Tier Limitations**

#### **Problem**: Services sleeping after 15 minutes
```
Service responding slowly or timing out
```

#### **Solution**: Understanding Free Tier Behavior
- Services sleep after 15 minutes of inactivity
- First request takes 30-60 seconds to wake up
- 750 hours per month per service
- Consider paid plan for production use

### **Cold Start Optimization**

#### **Solution**: Keep Services Warm (Optional)
```bash
# Setup periodic health checks (every 10 minutes)
curl https://your-service.onrender.com/health
```

## 🔍 **Debugging Steps**

### **1. Check Service Logs**
- Go to Render Dashboard → Service → Logs tab
- Look for startup errors, dependency failures, or runtime issues

### **2. Verify Environment Variables**
- Service → Environment tab
- Ensure all required variables are set
- Check for typos in variable names

### **3. Test Service Health**
```bash
# Test each service individually
curl https://pdf-converter-auth-service.onrender.com/health
curl https://pdf-converter-library-service.onrender.com/health
curl https://pdf-converter-api-gateway.onrender.com/health
```

### **4. Local Testing**
```bash
# Test Docker build locally
cd services/auth-service
docker build -f Dockerfile -t test-service ../../

# Test with environment variables
docker run -e SUPABASE_URL=test -e JWT_SECRET_KEY=test test-service
```

## 📞 **Getting Help**

### **Render Support**
- Check Render status page for outages
- Review Render documentation for service limits
- Contact Render support for platform issues

### **Project Issues**
- Check GitHub issues for similar problems
- Review commit history for recent changes
- Create detailed issue with logs and configuration

---

**Most Common Issues Fixed:**
1. ✅ Pydantic v2 compatibility (BaseSettings, regex→pattern, email-validator)
2. ✅ Dependency conflicts (httpx + supabase versions)  
3. ✅ Missing environment variables (Supabase, JWT secrets)
4. ✅ Incorrect Dockerfile paths in Render configuration
5. ✅ Frontend API URL routing through gateway

**Last Updated**: January 2025 