FROM python:3.10-slim

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar app
COPY app.py .

# RunPod serverless maneja el puerto internamente

CMD ["python", "app.py"]
