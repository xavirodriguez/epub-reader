"""
Implementación de Bark TTS.
Motor experimental con capacidades emocionales avanzadas.
https://github.com/suno-ai/bark
"""
import asyncio
import numpy as np
from typing import Dict, Any, Optional
from bark import SAMPLE_RATE, generate_audio, preload_models
from bark.generation import SAMPLE_RATE as BARK_SAMPLE_RATE
from app.models.tts.base_tts import BaseTTSService, TTSEngine
from app.core.logger import logger
from app.core.exceptions import TTSException


class BarkTTSService(BaseTTSService):
    """
    Servicio Bark TTS.
    Alta calidad con emociones naturales, pero más lento.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine_name = TTSEngine.BARK
        self.use_gpu = config.get("use_gpu", False)
        self.use_small_models = config.get("small_models", True)
        self.sample_rate = BARK_SAMPLE_RATE

        # Presets de voz para catalán (experimental)
        self.voice_presets = {
            "narradora": "v2/es_speaker_6",  # Voz femenina (español cercano)
            "harry": "v2/es_speaker_3"       # Voz joven
        }

    async def initialize(self) -> bool:
        """Precargar modelos de Bark"""
        try:
            logger.info("Loading Bark models (this may take a while)...")

            # Precargar modelos en executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: preload_models(
                    text_use_gpu=self.use_gpu,
                    coarse_use_gpu=self.use_gpu,
                    fine_use_gpu=self.use_gpu,
                    codec_use_gpu=self.use_gpu,
                    text_use_small=self.use_small_models,
                    coarse_use_small=self.use_small_models,
                    fine_use_small=self.use_small_models
                )
            )

            self.is_ready = True
            logger.info("Bark TTS initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Bark initialization failed: {e}")
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
        Generar audio con Bark.

        NOTA: Bark no soporta catalán nativamente.
        Usa español como aproximación.

        Args:
            text: Texto a sintetizar
            voice: Voz (narradora, harry)
            language: Idioma (ignorado, usa ES)

        Returns:
            Audio PCM int16
        """
        if not self.is_ready:
            raise TTSException("Bark service not initialized")

        if not text.strip():
            raise TTSException("Empty text")

        # ADVERTENCIA: Bark no tiene catalán nativo
        if language.startswith("ca"):
            logger.warning("Bark doesn't support Catalan, using Spanish voice")

        try:
            # Seleccionar preset de voz
            history_prompt = self.voice_presets.get(
                voice.lower(),
                self.voice_presets["narradora"]
            )

            # Generar audio (operación lenta)
            loop = asyncio.get_event_loop()
            audio_array = await loop.run_in_executor(
                None,
                lambda: generate_audio(
                    text,
                    history_prompt=history_prompt,
                    text_temp=0.7,
                    waveform_temp=0.7
                )
            )

            # Convertir a int16
            audio_int16 = (audio_array * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            logger.info(f"Generated {len(audio_bytes)} bytes with Bark ({voice})")
            return audio_bytes

        except Exception as e:
            logger.error(f"Bark generation error: {e}")
            raise TTSException(f"Bark error: {str(e)}")

    async def list_voices(self, language: Optional[str] = None) -> Dict[str, Any]:
        """Listar presets disponibles"""
        return {
            "engine": "bark",
            "voices": self.voice_presets,
            "note": "Bark uses Spanish voices as Catalan approximation"
        }

    async def health_check(self) -> bool:
        """Health check"""
        # Bark es muy lento para generar audio en cada check
        # Solo verificamos que el servicio esté marcado como listo
        return self.is_ready

    async def shutdown(self):
        """Limpiar modelos de memoria"""
        # Bark no tiene método específico de cleanup
        logger.info("Bark TTS shutdown")
