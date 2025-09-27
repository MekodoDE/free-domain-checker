# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for whois functionality
RUN apt-get update && apt-get install -y \
    whois \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main script
COPY main.py .

# Create a non-root user for security
RUN useradd -m -u 1000 domainchecker && chown -R domainchecker:domainchecker /app
USER domainchecker

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the domain checker
CMD ["python", "main.py"]