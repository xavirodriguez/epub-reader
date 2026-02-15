# Multi-stage build para optimizar tamaño
FROM python:3.12-slim as base

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Stage: Piper TTS ---
FROM base as piper-installer

# Descargar e instalar Piper TTS
RUN curl -L https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    -o piper.tar.gz && \
    tar -xzf piper.tar.gz && \
    mv piper/piper /usr/local/bin/ && \
    chmod +x /usr/local/bin/piper && \
    rm -rf piper piper.tar.gz

# Descargar modelos catalanes
RUN mkdir -p /models/piper && \
    cd /models/piper && \
    curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/ca/ca_ES/upc_ona/medium/ca_ES-upc_ona-medium.onnx \
    -o ca_ES-upc_ona-medium.onnx && \
    curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/ca/ca_ES/upc_ona/medium/ca_ES-upc_ona-medium.onnx.json \
    -o ca_ES-upc_ona-medium.onnx.json

# --- Stage: Final ---
FROM base

# Copiar Piper desde stage anterior
COPY --from=piper-installer /usr/local/bin/piper /usr/local/bin/piper
COPY --from=piper-installer /models/piper /models/piper

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /tmp/epub_narrator_exports && \
    chmod 777 /tmp/epub_narrator_exports

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ping || exit 1

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
