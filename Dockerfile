FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Instalar Python 3.10 y dependencias del sistema
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Crear symlinks para python (si no existen)
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar app
COPY app.py .

# RunPod serverless maneja el puerto internamente

CMD ["python", "app.py"]
