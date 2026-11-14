#!/usr/bin/env bash
# Build script for Render. Python stays required. PDFCalque is the EPUB writer.

set -o errexit

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p /tmp/uploads
mkdir -p /tmp/outputs

# The library source is in pdfcalque/. One compile job uses less memory.
# A failed compile does not stop the deploy: Poppler can still convert.
build_pdfcalque() {
  if ! command -v cargo >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable || return 1
    # shellcheck disable=SC1091
    . "$HOME/.cargo/env"
  fi
  export CARGO_BUILD_JOBS=1
  export CARGO_TARGET_DIR=/tmp/pdfcalque-target
  cargo build --release --manifest-path pdfcalque/Cargo.toml --bin pdfcalque || return 1
  mkdir -p bin
  cp /tmp/pdfcalque-target/release/pdfcalque bin/pdfcalque
  chmod +x bin/pdfcalque
}

if [ -f pdfcalque/Cargo.toml ]; then
  echo "Building PDFCalque..."
  if build_pdfcalque; then
    echo "PDFCalque binary is ready"
  else
    echo "PDFCalque build failed; Poppler fallback stays available"
  fi
fi

echo "Build completed successfully!"
echo "Python version: $(python --version)"
