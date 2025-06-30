# 🚀 Deployment Checklist - Quick Reference

## ✅ Pre-deployment

- [ ] Supabase project created and configured
- [ ] Database schema applied (from `database/supabase_schema.sql`)
- [ ] `.env` file created from `.env.template`
- [ ] All environment variables populated
- [ ] Code committed and pushed to GitHub

## 🔧 Environment Variables Required

### All Services Need:
- `JWT_SECRET_KEY` (same across all services)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### Additional for Library Service:
- `CLOUDINARY_URL`

### Additional for Converter Service:
- `LIBRARY_SERVICE_URL` (after library service is deployed)

## 🚀 Deployment Order

1. **Auth Service** → `pdf-converter-auth-service`
2. **Library Service** → `pdf-converter-library-service`  
3. **API Gateway** → `pdf-converter-api-gateway`
4. **Update Converter** → Add environment variables

## 📊 Expected Service URLs

- **API Gateway**: `https://pdf-converter-api-gateway.onrender.com`
- **Auth Service**: `https://pdf-converter-auth-service.onrender.com`
- **Library Service**: `https://pdf-converter-library-service.onrender.com`
- **Converter Service**: `https://pdf-epub-converter-api.onrender.com` (existing)

## 🧪 Quick Tests

```bash
# Health checks
curl https://pdf-converter-api-gateway.onrender.com/health
curl https://pdf-converter-auth-service.onrender.com/health
curl https://pdf-converter-library-service.onrender.com/health

# Auth flow
curl -X POST https://pdf-converter-api-gateway.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'
```

## ⚡ Quick Deploy Script

Run the automated deployment helper:

```bash
./deploy.sh
```

This will:
- ✅ Validate environment variables
- ✅ Check git status
- ✅ Generate render.yaml blueprint
- ✅ Show deployment instructions

## 🔧 Troubleshooting

### Service won't start?
- Check environment variables are set
- Verify JWT_SECRET_KEY is identical across services
- Check logs in Render dashboard

### Database connection fails?
- Verify Supabase URL and Service Key
- Check database schema is applied
- Ensure RLS policies are enabled

### Build fails?
- Verify Dockerfile paths
- Check Docker Context is set to "." (repo root)
- Ensure shared/ directory is accessible

---

**💡 Pro Tips:**
- Services sleep after 15 minutes of inactivity (free tier)
- First request after sleep takes ~30-60 seconds
- Use health endpoints to keep services warm
- Monitor logs during initial deployment 