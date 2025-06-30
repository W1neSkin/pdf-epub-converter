# 🏗️ Microservices Setup Guide

## Overview

This guide will help you set up the PDF to EPUB Converter with a **free microservices architecture** using:

- **Supabase** (Free PostgreSQL + Auth)
- **Render** (Free Web Services)
- **GitHub Pages** (Free Frontend Hosting)
- **Cloudinary** (Free File Storage)

## 🏛️ Architecture

```
GitHub Pages (Frontend)
         ↓
API Gateway (Render Free)
         ↓
┌─────────────┬─────────────┬─────────────┐
│Auth Service │ Converter   │ Library     │
│(Render Free)│ (Current)   │(Render Free)│  
└─────────────┴─────────────┴─────────────┘
         ↓
Supabase (PostgreSQL + Auth + Storage) - FREE
Cloudinary (Current usage) - FREE
```

## 📋 Prerequisites

1. **Supabase Account** (free tier)
2. **Render Account** (free tier)
3. **GitHub Account** (existing)
4. **Cloudinary Account** (existing)

## 🚀 Step 1: Setup Supabase

### 1.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up/login and create a new project
3. Choose a name: `pdf-epub-converter`
4. Set a secure database password
5. Wait for project initialization

### 1.2 Setup Database Schema

1. Go to **SQL Editor** in your Supabase dashboard
2. Copy and paste the content from `database/supabase_schema.sql`
3. Click **Run** to create all tables and policies

### 1.3 Get Supabase Credentials

1. Go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://your-project.supabase.co`
   - **anon public key**: `eyJ...`
   - **service_role secret key**: `eyJ...`

### 1.4 Configure Row Level Security

The schema automatically sets up RLS policies, but verify:
1. Go to **Authentication** → **Policies**
2. Ensure all tables have policies enabled

## 🔧 Step 2: Environment Configuration

### 2.1 Create Environment File

```bash
# Copy the template
cp env.template .env

# Edit with your actual values
nano .env
```

### 2.2 Fill in Supabase Values

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database URL (from Supabase Settings → Database)
DATABASE_URL=postgresql://postgres.your-ref:password@aws-0-region.pooler.supabase.com:5432/postgres

# Generate a secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)
```

## 📦 Step 3: Deploy Services to Render

### 3.1 Deploy Auth Service

1. **Create New Web Service** on Render
2. **Connect GitHub** repository
3. **Service Configuration**:
   ```
   Name: pdf-auth-service
   Environment: Docker
   Dockerfile Path: services/auth-service/Dockerfile
   Region: Choose closest to you
   Branch: master
   ```
4. **Environment Variables** (add all from .env):
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   JWT_SECRET=your-jwt-secret
   PORT=8001
   ```
5. **Deploy** and wait for completion
6. **Copy Service URL**: `https://pdf-auth-service.onrender.com`

### 3.2 Deploy Library Service

1. **Create New Web Service** on Render
2. **Service Configuration**:
   ```
   Name: pdf-library-service
   Environment: Docker
   Dockerfile Path: services/library-service/Dockerfile
   ```
3. **Environment Variables**:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   JWT_SECRET=your-jwt-secret
   CLOUDINARY_URL=your-cloudinary-url
   PORT=8002
   ```
4. **Deploy** and copy URL: `https://pdf-library-service.onrender.com`

### 3.3 Deploy API Gateway

1. **Create New Web Service** on Render
2. **Service Configuration**:
   ```
   Name: pdf-api-gateway
   Environment: Docker
   Dockerfile Path: services/api-gateway/Dockerfile
   ```
3. **Environment Variables**:
   ```
   JWT_SECRET=your-jwt-secret
   AUTH_SERVICE_URL=https://pdf-auth-service.onrender.com
   CONVERTER_SERVICE_URL=https://pdf-epub-converter-api.onrender.com
   LIBRARY_SERVICE_URL=https://pdf-library-service.onrender.com
   FRONTEND_URL=https://w1neskin.github.io/pdf-epub-converter
   PORT=8080
   ```
4. **Deploy** and copy URL: `https://pdf-api-gateway.onrender.com`

### 3.4 Update Existing Converter Service

1. **Go to existing Render service**: `pdf-epub-converter-api`
2. **Add Environment Variables**:
   ```
   JWT_SECRET=your-jwt-secret
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   DATABASE_URL=your-database-url
   ```
3. **Redeploy** to pick up new environment variables

## 🌐 Step 4: Update Frontend

### 4.1 Update API URL

1. **Edit** `frontend/src/components/PdfUploader.js`
2. **Change API_BASE_URL**:
   ```javascript
   const API_BASE_URL = 'https://pdf-api-gateway.onrender.com';
   ```

### 4.2 Add Authentication Support

The frontend will need updates to handle user authentication. This will be implemented in the next phase.

## 🧪 Step 5: Test the System

### 5.1 Test Individual Services

```bash
# Test Auth Service
curl https://pdf-auth-service.onrender.com/

# Test Library Service  
curl https://pdf-library-service.onrender.com/

# Test API Gateway
curl https://pdf-api-gateway.onrender.com/health
```

### 5.2 Test Authentication Flow

```bash
# Register a user
curl -X POST https://pdf-api-gateway.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Login
curl -X POST https://pdf-api-gateway.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## 🔧 Step 6: Local Development

### 6.1 Run with Docker Compose

```bash
# Start all services locally
docker-compose -f docker-compose.microservices.yml up

# Or start specific services
docker-compose -f docker-compose.microservices.yml up api-gateway auth-service
```

### 6.2 Access Services

- **API Gateway**: http://localhost:8080
- **Frontend**: http://localhost:3000
- **Auth Service**: http://localhost:8001 (internal)
- **Converter Service**: http://localhost:8000 (internal)
- **Library Service**: http://localhost:8002 (internal)

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check all services
curl https://pdf-api-gateway.onrender.com/health

# Individual service health
curl https://pdf-auth-service.onrender.com/health
curl https://pdf-library-service.onrender.com/health
```

### Database Monitoring

1. **Supabase Dashboard** → **Database** → **Monitor**
2. Check connection pools, slow queries, storage usage

### Free Tier Limits

- **Render**: 750 hours/month per service (enough for 4 services)
- **Supabase**: 500MB database, 1GB storage, 50MB file uploads
- **Cloudinary**: 25GB storage, 25GB bandwidth/month

## 🚨 Troubleshooting

### Common Issues

1. **Service timeouts on Render**
   - Services sleep after 15 minutes of inactivity
   - First request after sleep takes ~30 seconds

2. **CORS errors**
   - Ensure FRONTEND_URL is set correctly in all services
   - Check ALLOWED_ORIGINS in shared/config.py

3. **Database connection errors**
   - Verify DATABASE_URL format
   - Check Supabase project status
   - Ensure RLS policies are correct

4. **JWT token errors**
   - Ensure JWT_SECRET is same across all services
   - Check token expiration (24 hours default)

### Logs

```bash
# View service logs on Render
# Go to Service → Logs tab in Render dashboard

# Local development logs
docker-compose -f docker-compose.microservices.yml logs -f service-name
```

## 🎯 Next Steps

1. **Phase 1**: Get basic auth + gateway working
2. **Phase 2**: Add library service with book management
3. **Phase 3**: Update frontend with auth UI
4. **Phase 4**: Add advanced features (sharing, analytics)

## 💰 Cost Breakdown

| Service | Cost | Usage |
|---------|------|-------|
| Supabase | FREE | 500MB DB + Auth + 1GB storage |
| Render (4 services) | FREE | 750 hours/month each |
| GitHub Pages | FREE | Static hosting |
| Cloudinary | FREE | Current usage |
| **Total** | **$0/month** | 🎉 |

## 🔐 Security Notes

1. **Environment Variables**: Never commit `.env` to git
2. **JWT Secret**: Use strong random string in production
3. **Database**: RLS policies protect user data
4. **HTTPS**: All services use HTTPS by default on Render
5. **Secrets**: Store sensitive data in Render environment variables

---

**Ready to implement?** Let me know if you want to proceed with any specific step! 