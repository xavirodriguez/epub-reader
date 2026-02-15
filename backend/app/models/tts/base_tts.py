"""
Interfaz abstracta para motores TTS.
Todos los engines deben implementar esta interfaz.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum


class TTSEngine(str, Enum):
    """Motores TTS disponibles"""
    PIPER = "piper"
    COQUI = "coqui"
    BARK = "bark"
    GEMINI = "gemini"


class VoiceGender(str, Enum):
    """Género de voz"""
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"


class BaseTTSService(ABC):
    """
    Clase base abstracta para servicios TTS.
    Define la interfaz que todos los engines deben implementar.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar servicio TTS.

        Args:
            config: Configuración específica del engine
        """
        self.config = config
        self.engine_name: TTSEngine = TTSEngine.PIPER
        self.is_ready = False

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Inicializar modelos y recursos.

        Returns:
            True si inicialización exitosa
        """
        pass

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        voice: str = "default",
        language: str = "ca",
        **kwargs
    ) -> bytes:
        """
        Generar audio desde texto.

        Args:
            text: Texto a convertir
            voice: Nombre de la voz
            language: Código de idioma (ca, ca-valencia)
            **kwargs: Parámetros adicionales específicos del engine

        Returns:
            Audio en formato PCM int16 (bytes)

        Raises:
            TTSException: Error en generación
        """
        pass

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Listar voces disponibles.

        Args:
            language: Filtrar por idioma

        Returns:
            Dict con información de voces disponibles
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verificar salud del servicio.

        Returns:
            True si el servicio está operativo
        """
        pass

    async def shutdown(self):
        """Liberar recursos (opcional)"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Información del engine.

        Returns:
            Metadata del engine
        """
        return {
            "engine": self.engine_name.value,
            "ready": self.is_ready,
            "config": self.config
        }
