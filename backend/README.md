# EPUB Narrator Backend

Backend en Python 3.12 para el sistema de narración híbrido.

## 🛠 Tecnologías
- **FastAPI**: Framework web async.
- **Celery**: Tareas asíncronas para exportación de capítulos.
- **Redis**: Caché y broker de mensajes.
- **TTS Engines**: Piper, Coqui TTS, Bark.
- **LLM**: Ollama (Llama 3.2).

## 🚀 Instalación Local

1. Crear entorno virtual:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar `.env`:
```bash
cp .env.example .env
# Editar .env con tus claves y rutas
```

4. Ejecutar:
```bash
uvicorn app.main:app --reload
```

## 📦 Workers (Celery)
Para la exportación de capítulos, es necesario iniciar el worker:
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## 🧪 Testing
```bash
python scripts/test_tts_engines.py
```
