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

# Next to the Python files. A bin/ directory is gitignored and disappears
# from the running service, so the program was never found.
echo "Downloading PDFCalque..."
curl -fL --retry 3 -o pdfcalque_bin \
  https://github.com/W1neSkin/PDFCalque/releases/download/linux/pdfcalque
chmod +x pdfcalque_bin
test -s pdfcalque_bin

echo "PDFCalque binary is ready"
echo "Build completed successfully!"
echo "Python version: $(python --version)"
