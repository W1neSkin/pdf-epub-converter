# 🚀 Render Deployment Guide

## Prerequisites

1. ✅ Supabase project created (follow `setup_supabase.md`)
2. ✅ `.env` file updated with Supabase credentials
3. ✅ Database schema created in Supabase
4. ✅ Code committed and pushed to GitHub

## Deploy Services in Order

### 1. Deploy Auth Service

1. **Go to [render.com](https://render.com)**
2. **Click "New +" → "Web Service"**
3. **Connect GitHub** repository: `pdf-epub-converter`
4. **Service Configuration**:
   ```
   Name: pdf-auth-service
   Environment: Docker
   Region: Choose closest to you
   Branch: master
   Dockerfile Path: services/auth-service/Dockerfile
   ```

5. **Environment Variables** (click "Advanced"):
   ```
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   DATABASE_URL=postgresql://postgres.your-ref:password@...
   JWT_SECRET=ffc42dc7409a15e229d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
   PORT=8001
   ENVIRONMENT=production
   DEBUG=false
   LOG_LEVEL=INFO
   ```

6. **Click "Create Web Service"**
7. **Wait for deployment** (~5-10 minutes)
8. **Copy service URL**: `https://pdf-auth-service.onrender.com`

### 2. Deploy API Gateway

1. **Create another Web Service**
2. **Service Configuration**:
   ```
   Name: pdf-api-gateway
   Environment: Docker
   Dockerfile Path: services/api-gateway/Dockerfile
   ```

3. **Environment Variables**:
   ```
   JWT_SECRET=ffc42dc7409a15e229d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
   AUTH_SERVICE_URL=https://pdf-auth-service.onrender.com
   CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
   LIBRARY_SERVICE_URL=https://pdf-library-service.onrender.com
   FRONTEND_URL=https://w1neskin.github.io/pdf-epub-converter
   PORT=8080
   ENVIRONMENT=production
   DEBUG=false
   LOG_LEVEL=INFO
   ```

4. **Deploy and copy URL**: `https://pdf-api-gateway.onrender.com`

### 3. Update Existing Converter Service

1. **Go to your existing service**: `pdf-epub-converter-api`
2. **Environment** → **Add Environment Variables**:
   ```
   JWT_SECRET=ffc42dc7409a15e229d6f9b86c2ab5dd8d641f75d0c54bd5e408836230126013
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   DATABASE_URL=postgresql://postgres.your-ref:password@...
   ```
3. **Manual Deploy** to restart with new environment

## Test Deployment

```bash
# Test Auth Service
curl https://pdf-auth-service.onrender.com/

# Test API Gateway
curl https://pdf-api-gateway.onrender.com/health

# Test registration
curl -X POST https://pdf-api-gateway.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Test login
curl -X POST https://pdf-api-gateway.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## Update Frontend

1. **Edit** `frontend/src/components/PdfUploader.js`
2. **Change API_BASE_URL**:
   ```javascript
   const API_BASE_URL = 'https://pdf-api-gateway.onrender.com';
   ```
3. **Commit and push** to deploy via GitHub Actions

## Troubleshooting

### Common Issues:

1. **Build fails**: Check Dockerfile paths are correct
2. **Service won't start**: Check environment variables
3. **Database connection fails**: Verify DATABASE_URL format
4. **Auth fails**: Ensure JWT_SECRET is same across services

### Check Logs:
1. Go to service in Render dashboard
2. Click **"Logs"** tab
3. Look for error messages

### Service Status:
- Services may sleep after 15 minutes of inactivity (free tier)
- First request after sleep takes ~30 seconds to wake up

---

**After deployment**, your architecture will be:
```
GitHub Pages → API Gateway → Auth Service
                ↓           ↓
            Converter ← → Supabase
```

All communication goes through the gateway! 🎉 