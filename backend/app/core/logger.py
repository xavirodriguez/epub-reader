"""
Sistema de logging estructurado con JSON.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings


def setup_logger(name: str = "epub_narrator") -> logging.Logger:
    """
    Configura logger con formato JSON para producción.

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Evitar duplicados
    if logger.handlers:
        return logger

    # Handler consola
    handler = logging.StreamHandler(sys.stdout)

    # Formato según entorno
    if settings.ENVIRONMENT == "production":
        # JSON en producción
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # Legible en desarrollo
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Logger global
logger = setup_logger()
