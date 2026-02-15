"""
Inyección de dependencias para FastAPI.
"""
from typing import Generator
from app.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Dependencia para obtener configuración"""
    return get_settings()
