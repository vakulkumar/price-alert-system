FROM python:3.11-slim

WORKDIR /app

# Copy shared module first
COPY shared /app/shared

# Copy service requirements and install
COPY gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY gateway /app/gateway

WORKDIR /app/gateway

# Expose API port
EXPOSE 8000

# Run the service
CMD ["python", "main.py"]
