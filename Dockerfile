# Use Python slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose Cloud Run default port
EXPOSE 8080

# Run with Gunicorn (Cloud Run requirement)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
