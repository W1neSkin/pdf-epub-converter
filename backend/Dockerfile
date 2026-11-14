# EPUB is written by PDFCalque. Poppler remains for vector-only pages.
FROM rust:1-bookworm AS pdfcalque
WORKDIR /src
COPY pdfcalque /src
RUN cargo build --release --bin pdfcalque

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=pdfcalque /src/target/release/pdfcalque /usr/local/bin/pdfcalque

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
