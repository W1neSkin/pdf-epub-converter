#!/bin/bash

# 🚀 PDF to EPUB Converter - Microservices Deployment Script
# This script helps automate the deployment process for Render services

set -e  # Exit on any error

echo "🚀 PDF to EPUB Converter - Deployment Helper"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_status "Please create .env file from .env.template first"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
validate_env() {
    print_status "Validating environment variables..."
    
    required_vars=(
        "SUPABASE_URL"
        "SUPABASE_SERVICE_KEY"
        "JWT_SECRET_KEY"
        "CLOUDINARY_URL"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        print_status "Please update your .env file and try again"
        exit 1
    fi
    
    print_success "Environment variables validated"
}

# Check git status
check_git() {
    print_status "Checking git status..."
    
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "You have uncommitted changes"
        echo ""
        git status --short
        echo ""
        read -p "Do you want to commit and push changes? (y/n): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Committing changes..."
            git add .
            git commit -m "Deploy: Updated configuration for microservices deployment"
            git push origin master
            print_success "Changes committed and pushed"
        else
            print_warning "Proceeding with deployment (uncommitted changes won't be deployed)"
        fi
    else
        print_success "Git working directory is clean"
    fi
}

# Generate Render blueprint
generate_render_blueprint() {
    print_status "Generating render.yaml blueprint..."
    
    cat > render.yaml << EOF
services:
  # Auth Service
  - type: web
    name: pdf-converter-auth-service
    runtime: docker
    dockerfilePath: ./services/auth-service/Dockerfile
    dockerContext: .
    plan: free
    region: oregon
    branch: master
    healthCheckPath: /health
    buildFilter:
      paths:
        - services/auth-service/**
        - shared/**
    envVars:
      - key: SUPABASE_URL
        value: ${SUPABASE_URL}
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: JWT_SECRET_KEY
        sync: false
      - key: PORT
        value: "8001"
      - key: DEBUG
        value: "false"
      - key: LOG_LEVEL
        value: "INFO"

  # Library Service
  - type: web
    name: pdf-converter-library-service
    runtime: docker
    dockerfilePath: ./services/library-service/Dockerfile
    dockerContext: .
    plan: free
    region: oregon
    branch: master
    healthCheckPath: /health
    buildFilter:
      paths:
        - services/library-service/**
        - shared/**
    envVars:
      - key: SUPABASE_URL
        value: ${SUPABASE_URL}
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: CLOUDINARY_URL
        sync: false
      - key: JWT_SECRET_KEY
        sync: false
      - key: PORT
        value: "8002"
      - key: DEBUG
        value: "false"
      - key: LOG_LEVEL
        value: "INFO"

  # API Gateway
  - type: web
    name: pdf-converter-api-gateway
    runtime: docker
    dockerfilePath: ./services/api-gateway/Dockerfile
    dockerContext: .
    plan: free
    region: oregon
    branch: master
    healthCheckPath: /health
    buildFilter:
      paths:
        - services/api-gateway/**
        - shared/**
    envVars:
      - key: JWT_SECRET_KEY
        sync: false
      - key: AUTH_SERVICE_URL
        value: https://pdf-converter-auth-service.onrender.com
      - key: CONVERTER_SERVICE_URL
        value: https://pdf-epub-converter-api.onrender.com
      - key: LIBRARY_SERVICE_URL
        value: https://pdf-converter-library-service.onrender.com
      - key: PORT
        value: "8080"
      - key: DEBUG
        value: "false"
      - key: LOG_LEVEL
        value: "INFO"
EOF

    print_success "render.yaml blueprint generated"
}

# Display deployment instructions
display_instructions() {
    print_success "🎉 Ready for deployment!"
    echo ""
    echo "📋 Next steps:"
    echo ""
    echo "1. 🌐 Go to https://render.com and sign in"
    echo "2. 📁 Click 'New +' → 'Blueprint'"
    echo "3. 🔗 Connect your GitHub repository: W1neSkin/pdf-epub-converter"
    echo "4. 📄 Select the generated render.yaml file"
    echo "5. 🔐 Add sensitive environment variables:"
    echo "   - SUPABASE_SERVICE_KEY"
    echo "   - JWT_SECRET_KEY"
    echo "   - CLOUDINARY_URL"
    echo "6. 🚀 Click 'Apply' to deploy all services"
    echo ""
    echo "⏱️  Deployment will take ~10-15 minutes"
    echo ""
    echo "📊 Service URLs (after deployment):"
    echo "   - API Gateway: https://pdf-converter-api-gateway.onrender.com"
    echo "   - Auth Service: https://pdf-converter-auth-service.onrender.com"
    echo "   - Library Service: https://pdf-converter-library-service.onrender.com"
    echo ""
    echo "🧪 Test deployment with:"
    echo "   curl https://pdf-converter-api-gateway.onrender.com/health"
    echo ""
    print_warning "Don't forget to update your existing converter service with:"
    echo "   - LIBRARY_SERVICE_URL=https://pdf-converter-library-service.onrender.com"
    echo "   - JWT_SECRET_KEY=[your-jwt-secret]"
    echo "   - SUPABASE_URL=[your-supabase-url]"
    echo "   - SUPABASE_SERVICE_KEY=[your-service-key]"
}

# Main execution
main() {
    print_status "Starting deployment preparation..."
    echo ""
    
    validate_env
    echo ""
    
    check_git
    echo ""
    
    generate_render_blueprint
    echo ""
    
    display_instructions
}

# Run main function
main

print_success "🎉 Deployment preparation complete!"
print_status "Follow the instructions above to deploy to Render" 