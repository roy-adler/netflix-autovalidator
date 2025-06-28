# Use the official Playwright image with browsers preinstalled
FROM mcr.microsoft.com/playwright/python:v1.43.1-jammy

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command
CMD ["python", "main.py"]
