# ============================================
# GAS AUTOMATION - BACKEND API
# Adaptado para servidor 192.168.10.156
# ============================================

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    build-essential \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements from backend
COPY ../backend/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY ../backend/app ./app/
COPY ../backend/alembic ./alembic/
COPY ../backend/alembic.ini .
COPY ../backend/init_db.sql .

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Add current directory to Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

# Healthcheck (sem localhost)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://0.0.0.0:8000/health || exit 1

# Start the application with uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

