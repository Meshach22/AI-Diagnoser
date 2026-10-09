# Multi-service production base Dockerfile for AI-Diagnoser (Python 3.11)
FROM python:3.11-slim AS base

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV, PDF/Poppler parsing, Tesseract OCR, and C builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    poppler-utils \
    tesseract-ocr \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy requirements and install dependencies with clean pip cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Set correct ownership for application files
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose backend (8000) and frontend (8501) ports
EXPOSE 8000 8501

# Default command: Runs FastAPI backend (overridden by compose services)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
