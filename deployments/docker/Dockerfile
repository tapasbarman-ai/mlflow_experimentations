# Production Serving Image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# IMPORTANT: Copy the trained model database and artifacts into the container
# This makes the container self-contained for production
COPY mlflow.db .
COPY mlruns_artifacts/ ./mlruns_artifacts/

# Set Environment Variables for production serving
ENV MLFLOW_TRACKING_URI=sqlite:///app/mlflow.db
ENV MODEL_STAGE=Production
ENV PORT=8000

# Expose the API port
EXPOSE 8000

# Start the FastAPI serving service
CMD ["python", "src/serve.py"]
