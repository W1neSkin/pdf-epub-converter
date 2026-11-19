#!/usr/bin/env bash
# Build script for Render. Python stays required.
# The PDFCalque program is downloaded already built. Compiling Rust here
# ran out of memory and the deploy kept the old page renderer.

set -o errexit

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p /tmp/uploads
mkdir -p /tmp/outputs
mkdir -p bin

echo "Downloading PDFCalque..."
curl -fL --retry 3 -o bin/pdfcalque \
  https://github.com/W1neSkin/PDFCalque/releases/download/linux/pdfcalque
chmod +x bin/pdfcalque
test -s bin/pdfcalque

echo "PDFCalque binary is ready"
echo "Build completed successfully!"
echo "Python version: $(python --version)"
