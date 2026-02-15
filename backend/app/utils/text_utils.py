"""
Utilidades para procesamiento y limpieza de texto.
"""
import re
import unicodedata


def clean_epub_text(text: str) -> str:
    """
    Limpia el texto extraído de un EPUB eliminando artefactos comunes.
    """
    # Eliminar espacios múltiples y saltos de línea excesivos
    text = re.sub(r'\s+', ' ', text)

    # Eliminar caracteres de control
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

    # Eliminar URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

    return text.strip()


def normalize_catalan_text(text: str) -> str:
    """
    Normaliza caracteres específicos del catalán si es necesario.
    """
    # Asegurar que la l·l (ela geminada) use el carácter correcto
    text = text.replace('l.l', 'l·l').replace('L.L', 'L·L')

    return text


def estimate_reading_time(text: str) -> float:
    """
    Estima el tiempo de lectura en segundos (basado en ~150 palabras/min).
    """
    words = len(text.split())
    return (words / 150) * 60
