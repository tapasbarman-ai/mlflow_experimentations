# Use a lightweight Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core code and config
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Create folders for artifacts and MLflow runs
RUN mkdir -p /app/artifacts /app/mlruns

# Set Environment Variables
ENV MLFLOW_TRACKING_URI=file:///app/mlruns

# Default command: run the training pipeline
CMD ["python", "src/pipeline.py"]
