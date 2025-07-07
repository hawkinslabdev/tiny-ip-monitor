FROM python:3.14.0b3-alpine3.21

# Install system dependencies
RUN apk add --no-cache dcron tzdata

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
COPY templates/ ./templates/

# Create log directory
RUN mkdir -p /var/log && chmod 755 /var/log

# Expose web UI port
EXPOSE 8080

# Use Python startup script
CMD ["python", "startup.py"]