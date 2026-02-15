# EPUB Narrator - Sistema Híbrido Local + Cloud

Sistema completo de narración de EPUBs con TTS local y fallback a Gemini.

## 🚀 Quick Start

### Requisitos
- Docker & Docker Compose
- Python 3.12+ (para desarrollo local)
- Node.js 18+ (para frontend)
- GPU recomendada (pero no obligatoria)

### Instalación Rápida con Docker

1. **Clonar repositorio**
```bash
git clone <repo>
cd epub-narrator-hybrid
```

2. **Configurar variables de entorno**
```bash
cp backend/.env.example backend/.env
# Editar backend/.env con tus configuraciones
```

3. **Iniciar servicios**
```bash
docker-compose up -d
```

4. **Descargar modelos (primera vez)**
```bash
docker-compose exec backend python scripts/download_models.py
```

5. **Verificar salud**
```bash
curl http://localhost:8000/api/health
```

### Desarrollo Local

#### Backend
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Iniciar Ollama
ollama serve

# Iniciar FastAPI
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📚 Arquitectura

```
Frontend (React/Vite)
    ↓
Backend (FastAPI)
    ├── TTS Manager
    │   ├── Piper TTS (rápido)
    │   ├── Coqui TTS (calidad)
    │   └── Bark TTS (emocional)
    ├── LLM Service (Ollama)
    │   └── Speaker Detection
    ├── Cache (Redis)
    └── Workers (Celery)
        └── Chapter Export

Fallback → Gemini API
```

## 🎯 Endpoints Principales

### TTS
- `POST /api/tts/generate` - Generar audio
- `GET /api/tts/voices` - Listar voces
- `GET /api/tts/engines/status` - Estado engines

### Text Processing
- `POST /api/text/process` - Detectar speakers
- `POST /api/text/chunk` - Dividir texto

### Chapters
- `POST /api/chapters/export` - Exportar capítulo
- `GET /api/chapters/export/{task_id}/status` - Estado
- `GET /api/chapters/download/{task_id}` - Descargar

### Health
- `GET /api/health` - Health check completo
- `GET /api/health/ping` - Ping rápido

## 🔧 Configuración

Ver `backend/.env.example` para todas las opciones.

### Variables Clave

```bash
# TTS
DEFAULT_TTS_ENGINE=piper  # piper|coqui|bark
TTS_CACHE_ENABLED=true

# LLM
OLLAMA_MODEL=llama3.2

# Performance
MAX_CONCURRENT_TTS_JOBS=3
CHUNK_SIZE=1000
```

## 🧪 Testing

```bash
# Test engines TTS
python backend/scripts/test_tts_engines.py

# Health check
curl http://localhost:8000/api/health

# Test TTS generation
curl -X POST http://localhost:8000/api/tts/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola món","voice":"narradora","language":"ca"}'
```

## 📦 Componentes

### TTS Engines
- **Piper**: Rápido, eficiente, catalán nativo
- **Coqui**: Alta calidad, multilenguaje
- **Bark**: Emocional, experimental

### LLM
- **Ollama + Llama 3.2**: Detección de speakers y dialecto

### Cache
- **Redis**: Cache de audio, sesiones, resultados

### Workers
- **Celery**: Procesamiento asíncrono de capítulos

## 🐛 Troubleshooting

### Backend no inicia
```bash
# Verificar logs
docker-compose logs backend

# Reiniciar servicios
docker-compose restart
```

### Ollama no responde
```bash
# Verificar que Ollama está corriendo
docker-compose ps ollama

# Pull manual del modelo
docker-compose exec ollama ollama pull llama3.2
```

### TTS falla
```bash
# Test individual de engines
docker-compose exec backend python scripts/test_tts_engines.py
```

## 📊 Monitoreo

### Flower (Celery)
http://localhost:5555

### Logs
```bash
# Backend
docker-compose logs -f backend

# Celery worker
docker-compose logs -f celery-worker

# Todos
docker-compose logs -f
```

## 🚀 Producción

1. Cambiar `ENVIRONMENT=production` en `.env`
2. Configurar SSL/TLS
3. Usar Nginx como reverse proxy
4. Configurar backups de Redis
5. Monitoreo con Prometheus/Grafana

## 📄 Licencia

MIT

## 👥 Contribuciones

PRs bienvenidos!
