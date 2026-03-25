FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port (Railway sets PORT env var)
EXPOSE ${PORT:-8000}

# Start the FastAPI server
CMD cd backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
