# Use Python 3.12 as base image
FROM python:3.12-slim

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Backend is now just for PDF processing - no server needed
# Container can be used for running Python scripts manually or via API calls
CMD ["tail", "-f", "/dev/null"] 