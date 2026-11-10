FROM python:3.11-slim

# Install curl for debugging
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend code
COPY frontend/ /frontend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
