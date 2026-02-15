"""
Endpoints de health check y monitoreo.
"""
from fastapi import APIRouter
from app.api.schemas.tts import HealthCheckResponse
from app.models.tts.tts_manager import tts_manager
from app.models.llm.ollama_service import ollama_service
from app.core.cache import cache_manager
from app.core.logger import logger

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check completo del sistema.

    Verifica:
    - TTS engines
    - LLM service
    - Cache (Redis)

    Returns status: healthy/degraded/unhealthy
    """
    try:
        # Check TTS engines
        tts_health = await tts_manager.health_check()
        engines_healthy = any(tts_health.values())

        # Check LLM
        llm_healthy = await ollama_service.health_check()

        # Check cache
        cache_healthy = cache_manager.enabled and cache_manager.redis is not None
        if cache_healthy:
            try:
                await cache_manager.redis.ping()
            except:
                cache_healthy = False

        # Determinar estado general
        if engines_healthy and llm_healthy and cache_healthy:
            status = "healthy"
        elif engines_healthy:
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthCheckResponse(
            status=status,
            engines=tts_health,
            cache_available=cache_healthy,
            llm_available=llm_healthy
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            engines={},
            cache_available=False,
            llm_available=False
        )


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "ok", "message": "pong"}
