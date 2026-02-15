"""
FastAPI Application Principal.
Punto de entrada del backend.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.config import settings
from app.core.logger import logger
from app.core.cache import cache_manager
from app.core.exceptions import EPUBNarratorException

from app.models.tts.tts_manager import tts_manager
from app.models.llm.ollama_service import ollama_service

from app.api.routes import tts, text, chapters, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager para inicialización y cleanup.
    """
    # Startup
    logger.info("Starting EPUB Narrator Backend...")

    try:
        # Inicializar cache
        await cache_manager.connect()

        # Inicializar TTS Manager
        await tts_manager.initialize()

        # Inicializar LLM Service
        await ollama_service.initialize()

        logger.info("✓ All services initialized successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down EPUB Narrator Backend...")

    try:
        await tts_manager.shutdown()
        await cache_manager.disconnect()
        logger.info("✓ Clean shutdown completed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Crear app FastAPI
app = FastAPI(
    title="EPUB Narrator API",
    description="Backend híbrido para narración de EPUBs con TTS local y cloud",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Añadir header con tiempo de procesamiento"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(EPUBNarratorException)
async def epub_narrator_exception_handler(
    request: Request,
    exc: EPUBNarratorException
):
    """Handler para excepciones custom"""
    logger.error(f"Application error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


# Incluir routers
app.include_router(health.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(text.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint con info de la API"""
    return {
        "name": "EPUB Narrator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }


# Info endpoint
@app.get("/api/info")
async def api_info():
    """Información del sistema"""
    return {
        "environment": settings.ENVIRONMENT,
        "tts_engines": {
            "default": settings.DEFAULT_TTS_ENGINE,
            "available": ["piper", "coqui", "bark"]
        },
        "llm": {
            "provider": "ollama",
            "model": settings.OLLAMA_MODEL
        },
        "features": {
            "cache_enabled": settings.TTS_CACHE_ENABLED,
            "dialects": ["català", "valencià"],
            "max_text_length": settings.MAX_TEXT_LENGTH
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.API_WORKERS,
        log_level=settings.LOG_LEVEL.lower()
    )
