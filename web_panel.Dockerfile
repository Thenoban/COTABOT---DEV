# Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy web admin requirements
COPY web_admin/requirements_web.txt ./web_admin/

# Install Python dependencies
RUN pip install --no-cache-dir -r web_admin/requirements_web.txt

# Copy necessary files
COPY web_admin/ ./web_admin/
COPY database/ ./database/
COPY exceptions/ ./exceptions/
COPY config/ ./config/
COPY .env .env

# Create directory for database if not exists
RUN mkdir -p /app/data

# Expose port 5000
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Use gunicorn for production
CMD ["gunicorn", "--config", "web_admin/gunicorn_config.py", "web_admin.api:app"]
