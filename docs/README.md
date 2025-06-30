# 📚 PDF to EPUB Converter - Documentation

Welcome to the complete documentation for the PDF to EPUB Converter microservices project.

## 📋 Documentation Index

### 🚀 **Deployment Guides**
- **[Render Deployment Guide](./render-deploy.md)** - Complete step-by-step deployment to Render
- **[Supabase Setup](./setup_supabase.md)** - Database and authentication setup
- **[Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)** - Pre-deployment verification
- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues and solutions

### 🏗️ **Architecture & Development**  
- **[Microservices Setup](./MICROSERVICES_SETUP.md)** - Local development setup
- **[Phase 2 Implementation](./PHASE2_IMPLEMENTATION.md)** - Project roadmap
- **[API Documentation](./api-docs.md)** - Complete API reference
- **[Environment Configuration](./environment-setup.md)** - Environment variables guide

### 🔧 **Technical Guides**
- **[Docker Setup](./docker-guide.md)** - Container configuration
- **[Frontend Integration](./frontend-guide.md)** - Frontend setup and configuration
- **[Database Schema](./database-schema.md)** - Supabase database structure

## 🎯 **Quick Start**

1. **New to the project?** Start with [Environment Setup](./environment-setup.md)
2. **Ready to deploy?** Follow the [Render Deployment Guide](./render-deploy.md)  
3. **Having issues?** Check the [Troubleshooting Guide](./troubleshooting.md)

## 🌟 **Architecture Overview**

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

## 📞 **Support**

- **Issues**: Create an issue on GitHub
- **Documentation**: All guides are in this `docs/` folder
- **Updates**: Check commit history for latest changes

---

**Last Updated**: January 2025  
**Version**: 2.0.0 (Microservices Architecture) 