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

# Instalar PaddlePaddle GPU con build específico para CUDA 11.8.
# El paquete PyPI por defecto (paddlepaddle-gpu==2.5.2) apunta a CUDA 11.2 y
# falla con "Cannot load cudnn shared library" en imágenes CUDA 11.8.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir paddlepaddle-gpu==2.5.2.post117 \
       -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html

# Instalar el resto de dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download InsightFace buffalo_l model weights.
# Force CPUExecutionProvider explicitly so onnxruntime-gpu never touches CUDA
# during build (buildkit has no compatible CUDA driver).
RUN python -c "from insightface.app import FaceAnalysis; app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); app.prepare(ctx_id=-1)"

# Pre-download PaddleOCR models (CPU during build, GPU at runtime)
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)"

# Copiar app
COPY app.py .

# RunPod serverless maneja el puerto internamente

CMD ["python", "app.py"]
