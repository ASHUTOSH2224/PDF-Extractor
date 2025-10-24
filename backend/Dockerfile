FROM python:3.12-slim

# Install Java and system dependencies
# RUN apt-get update && \
#    apt-get install -y default-jre && \
#    apt-get clean

# Install PostgreSQL client & dev headers and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Python dependencies
# RUN pip install tabula-py JPype1

# Copy app code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

CMD ["gunicorn", "src.main:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000"]
