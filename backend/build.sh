#!/usr/bin/env bash
# Build script for Render. Install Python packages, including the PDFCalque module.

set -o errexit

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install --force-reinstall \
  https://github.com/W1neSkin/PDFCalque/releases/download/python/pdfcalque-cp312.whl

echo "Creating necessary directories..."
mkdir -p /tmp/uploads
mkdir -p /tmp/outputs

echo "Build completed successfully!"
echo "Python version: $(python --version)"
