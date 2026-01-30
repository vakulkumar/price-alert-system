FROM python:3.11-slim

WORKDIR /app

# Copy shared module first
COPY shared /app/shared

# Copy service requirements and install
COPY evaluator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY evaluator /app/evaluator

WORKDIR /app/evaluator

# Expose metrics port
EXPOSE 8002

# Run the service
CMD ["python", "main.py"]
