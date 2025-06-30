#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p /tmp/uploads
mkdir -p /tmp/outputs

echo "Build completed successfully!"
echo "Python version: $(python --version)" 