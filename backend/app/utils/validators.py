"""
Validadores personalizados para la API.
"""
from typing import Any
from app.core.exceptions import EPUBNarratorException


def validate_language_code(lang: str) -> bool:
    """Valida si el código de idioma es soportado"""
    supported = ["ca", "ca-valencia", "es", "en"]
    if lang.lower() not in supported:
        raise EPUBNarratorException(f"Language {lang} not supported. Use {supported}")
    return True


def is_valid_base64(s: str) -> bool:
    """Verifica si una cadena es base64 válido"""
    import base64
    try:
        if not s:
            return False
        return base64.b64encode(base64.b64decode(s)).decode('utf-8') == s
    except Exception:
        return False
