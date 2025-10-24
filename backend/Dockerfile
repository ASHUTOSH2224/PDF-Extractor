FROM python:3.12-slim

# Install system dependencies in a single layer to reduce image size
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*

# Set working directory in the container
WORKDIR /app

# Copy requirements.txt (adjust the path if your Dockerfile is in the backend folder)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for FastAPI app
EXPOSE 8000

# Use Gunicorn to run the FastAPI app with Uvicorn workers
CMD ["gunicorn", "src.main:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000"]
