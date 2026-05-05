# Smart HORECA AI — Dockerfile
# Build:  docker build -t horeca-ai .
# Run:    docker run -p 5000:5000 horeca-ai

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Train models on first build (dataset must be present)
RUN python train_models.py

# Expose port
EXPOSE 5000

# Run with Gunicorn (production)
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:5000", "run:app"]
