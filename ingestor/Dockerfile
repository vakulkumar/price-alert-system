FROM python:3.11-slim

WORKDIR /app

# Copy shared module first
COPY shared /app/shared

# Copy service requirements and install
COPY ingestor/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY ingestor /app/ingestor

WORKDIR /app/ingestor

# Expose metrics port
EXPOSE 8001

# Run the service
CMD ["python", "main.py"]
