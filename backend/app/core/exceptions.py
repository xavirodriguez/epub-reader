"""
Excepciones personalizadas de la aplicación.
"""
from fastapi import HTTPException, status


class EPUBNarratorException(Exception):
    """Excepción base de la aplicación"""
    pass


class TTSException(EPUBNarratorException):
    """Error en generación TTS"""
    pass


class LLMException(EPUBNarratorException):
    """Error en procesamiento LLM"""
    pass


class CacheException(EPUBNarratorException):
    """Error en sistema de caché"""
    pass


class ModelNotAvailableException(TTSException):
    """Modelo TTS no disponible"""
    pass


class QuotaExceededException(HTTPException):
    """Cuota API excedida"""
    def __init__(self, detail: str = "API quota exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


class ServiceUnavailableException(HTTPException):
    """Servicio no disponible"""
    def __init__(self, service: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service} is unavailable"
        )
