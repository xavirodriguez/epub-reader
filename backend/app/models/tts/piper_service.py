"""
Implementación de Piper TTS.
Motor rápido y eficiente para catalán.
https://github.com/rhasspy/piper
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from app.models.tts.base_tts import BaseTTSService, TTSEngine
from app.core.logger import logger
from app.core.exceptions import TTSException, ModelNotAvailableException


class PiperTTSService(BaseTTSService):
    """
    Servicio Piper TTS.
    Usa binario de Piper vía subprocess.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine_name = TTSEngine.PIPER
        self.binary_path = config.get("binary_path", "/usr/local/bin/piper")
        self.model_path = config.get("model_path")
        self.sample_rate = config.get("sample_rate", 24000)

        # Voces disponibles para catalán
        self.voices = {
            "narradora": {
                "model": "ca_ES-upc_ona-medium",
                "gender": "female",
                "description": "Voz femenina catalana estándar"
            },
            "harry": {
                "model": "ca_ES-upc_pau-medium",
                "gender": "male",
                "description": "Voz masculina joven catalana"
            }
        }

    async def initialize(self) -> bool:
        """Verificar binario y modelos"""
        try:
            # Verificar binario
            binary = Path(self.binary_path)
            if not binary.exists():
                logger.warning(f"Piper binary not found at {self.binary_path}")
                # No lanzamos excepción aquí para permitir que otros engines carguen
                self.is_ready = False
                return False

            # Verificar modelo por defecto
            if self.model_path:
                model = Path(self.model_path)
                if not model.exists():
                    logger.warning(f"Model not found: {self.model_path}")

            # Test básico
            process = await asyncio.create_subprocess_exec(
                self.binary_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise TTSException(f"Piper test failed: {stderr.decode()}")

            self.is_ready = True
            logger.info(f"Piper TTS initialized: {stdout.decode().strip()}")
            return True

        except Exception as e:
            logger.error(f"Piper initialization failed: {e}")
            self.is_ready = False
            return False

    async def generate_speech(
        self,
        text: str,
        voice: str = "narradora",
        language: str = "ca",
        **kwargs
    ) -> bytes:
        """
        Generar audio con Piper.

        Args:
            text: Texto a sintetizar
            voice: Nombre de voz (narradora, harry)
            language: Idioma (ca, ca-valencia)

        Returns:
            Audio PCM int16
        """
        if not self.is_ready:
            raise TTSException("Piper service not initialized")

        if not text.strip():
            raise TTSException("Empty text provided")

        # Seleccionar modelo según voz
        voice_config = self.voices.get(voice.lower(), self.voices["narradora"])
        model_name = voice_config["model"]

        # Adaptar para valenciano si es necesario
        if language == "ca-valencia":
            # Piper no tiene modelos específicos valencianos
            # Se usa el catalán estándar
            logger.debug("Using Catalan model for Valencian")

        try:
            # Ejecutar Piper
            process = await asyncio.create_subprocess_exec(
                self.binary_path,
                "--model", model_name,
                "--output-raw",  # PCM raw output
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Enviar texto y obtener audio
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=text.encode('utf-8')),
                timeout=30.0
            )

            if process.returncode != 0:
                raise TTSException(f"Piper generation failed: {stderr.decode()}")

            logger.info(f"Generated {len(stdout)} bytes with Piper ({voice})")
            return stdout

        except asyncio.TimeoutError:
            raise TTSException("Piper generation timeout")
        except Exception as e:
            logger.error(f"Piper error: {e}")
            raise TTSException(f"Piper generation error: {str(e)}")

    async def list_voices(self, language: Optional[str] = None) -> Dict[str, Any]:
        """Listar voces disponibles"""
        if language and not language.startswith("ca"):
            return {"voices": []}

        return {
            "engine": "piper",
            "voices": self.voices
        }

    async def health_check(self) -> bool:
        """Verificar que Piper funciona"""
        if not self.is_ready:
            return False

        try:
            # Test con texto corto
            await self.generate_speech("Test", voice="narradora")
            return True
        except Exception:
            return False
