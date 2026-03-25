FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project (backend + frontend)
COPY . .

# Set working directory to backend for runtime
WORKDIR /app/backend

CMD ["python", "start.py"]
