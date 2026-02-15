"""
Configuración centralizada de la aplicación.
Usa pydantic-settings para validación y tipado.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Literal


class Settings(BaseSettings):
    """Configuración principal de la aplicación"""

    # === General ===
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # === FastAPI ===
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_TTL: int = 3600

    # === Ollama ===
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT: int = 120

    # === TTS ===
    DEFAULT_TTS_ENGINE: Literal["piper", "coqui", "bark"] = "piper"
    TTS_SAMPLE_RATE: int = 24000
    TTS_CACHE_ENABLED: bool = True
    MAX_TEXT_LENGTH: int = 5000

    # Piper
    PIPER_MODEL_PATH: str = "/models/piper/ca_ES-upc_ona-medium"
    PIPER_BINARY_PATH: str = "/usr/local/bin/piper"

    # Coqui
    COQUI_MODEL: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    COQUI_USE_GPU: bool = False

    # Bark
    BARK_USE_GPU: bool = False
    BARK_SMALL_MODELS: bool = True

    # === Celery ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # === Gemini Fallback ===
    GEMINI_API_KEY: str = ""
    GEMINI_ENABLED: bool = True

    # === Performance ===
    MAX_CONCURRENT_TTS_JOBS: int = 3
    CHUNK_SIZE: int = 1000
    PRECACHE_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Obtener configuración singleton (cached).
    Uso: settings = get_settings()
    """
    return Settings()


# Exportar para uso directo
settings = get_settings()
