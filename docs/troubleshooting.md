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
JWT_SECRET=your-jwt-secret-here
```

### **Inter-Service Communication Issues**

#### **Problem**: Service dependencies unhealthy
```json
{"status":"degraded","dependencies":{"auth":"healthy","converter":"unhealthy:GET /health HTTP 502; GET / HTTP 503","library":"healthy"}}
```

The text after `unhealthy:` or `unavailable:` is the HTTP status or exception type. The gateway probes `GET /health`, then `GET /` when that call is a 404, a 5xx, or a connection error. A trailing slash on the service URL is ignored. A 429 is not followed by a second request.

#### **Problem**: Converter is HTTP 429 from the gateway and HTTP 200 from outside
```json
{"status":"degraded","dependencies":{"auth":"healthy","converter":"unhealthy:GET pdf-epub-scan.onrender.com/health HTTP 429 hibernate-rate-limited","library":"healthy"}}
```

Read the host in that string. It is the gateway's `CONVERTER_SERVICE_URL`, not whichever host you curled by hand. On 2026-11-22 the running gateway called `pdf-epub-scan.onrender.com`. A direct check of `pdf-epub-converter-api.onrender.com` returned 200 at the same time, because that is a different service. The blueprint file says `pdf-epub-converter-api`, but a manual deploy does not replace an env var already saved on the service.

`pdf-epub-scan` is up when `GET /` returns 200. It has no `/health` route (the app returns 404). Render's edge still answers the gateway's address with `429 hibernate-rate-limited` for several minutes after the app is serving other callers. A retry at 90 seconds landed inside that penalty and started the wait over, which is why one quiet minute was not enough. Cloudflare separately answers some proxied calls with HTTP 429, `cf-mitigated: challenge`, and a "Just a moment..." page that names `pdf-epub-scan.onrender.com`. That happens when the gateway forwards `CF-Ray` and `CF-Connecting-IP` from the incoming request to the next Cloudflare host.

#### **What to set on Render (do this in the dashboard; a deploy does not change it)**
Gateway service `srv-d1h8ovqli9vc73bg295g`, Environment:

```bash
CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
```

No trailing slash. Save, then redeploy the gateway so the process reads it. Use `pdf-epub-scan.onrender.com` only when proxied conversions should hit the Docker service that has Tesseract. The website already calls that host directly.

Free web services cannot receive Render private-network traffic, so an internal hostname will not work until the converter is on a paid plan.

#### **What the code does**
The gateway does not forward Cloudflare edge headers, and it does not send `GET /` after a 429. A normal probe is reused for 20 seconds. A 429 is reused for 3 minutes so the retry is not inside the penalty. `/health` names the host it called.

#### **How to verify after the env change and the deploy**
```bash
curl -sS https://pdf-converter-api-gateway.onrender.com/health
curl -sS https://pdf-epub-converter-api.onrender.com/health
curl -sS https://pdf-epub-scan.onrender.com/
curl -sS -D- https://pdf-converter-api-gateway.onrender.com/api/public/status/00000000-0000-0000-0000-000000000000
```
The gateway dependency for `converter` should be `healthy`, or it should name `pdf-epub-converter-api.onrender.com` if you set that URL. The proxied status call should be JSON `Conversion not found`, not an HTML challenge page. If it still says 429, wait 3 minutes and curl `/health` once. Do not curl it in a loop during that wait.

#### **Solution**: Update Service URLs
```bash
# API Gateway environment variables
AUTH_SERVICE_URL=https://pdf-converter-auth-service.onrender.com
CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com  
LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com

# Converter answers both paths. Render uses `/`. The gateway uses `/health`.
curl https://pdf-epub-converter-api.onrender.com/
curl https://pdf-epub-converter-api.onrender.com/health
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
JWT_SECRET=your-jwt-secret-here
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
curl https://pdf-epub-converter-api.onrender.com/health
curl https://pdf-epub-converter-api.onrender.com/
curl https://pdf-converter-api-gateway.onrender.com/health
```

### **4. Local Testing**
```bash
# Test Docker build locally
cd services/auth-service
docker build -f Dockerfile -t test-service ../../

# Test with environment variables
docker run -e SUPABASE_URL=test -e JWT_SECRET=test test-service
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