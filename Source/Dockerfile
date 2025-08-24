FROM python:3.12-alpine3.19

# Install system dependencies
RUN apk add --no-cache dcron tzdata wget

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY monitor.py .
COPY config.py .
COPY app.py .
COPY startup.py .
COPY test_logging.py .
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p /var/log /app/data && \
    chmod 755 /var/log /app/data

# Expose web UI port
EXPOSE 8080

# Use Python startup script
CMD ["python", "startup.py"]