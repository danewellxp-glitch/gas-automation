FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema para Firebird
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libfbclient2 \
    firebird-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
