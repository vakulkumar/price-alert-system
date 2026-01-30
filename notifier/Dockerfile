FROM python:3.11-slim

WORKDIR /app

# Copy shared module first
COPY shared /app/shared

# Copy service requirements and install
COPY notifier/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY notifier /app/notifier

WORKDIR /app/notifier

# Expose metrics port
EXPOSE 8003

# Run the service
CMD ["python", "main.py"]
