# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Cloud Run will override, but good practice)
EXPOSE 8080

# Run the app with Gunicorn for production
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 app:app
