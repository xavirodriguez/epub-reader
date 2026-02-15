"""
Implementación de Coqui TTS (XTTS v2).
Motor de alta calidad con clonación de voz.
https://github.com/coqui-ai/TTS
"""
import asyncio
import io
import numpy as np
import soundfile as sf
from typing import Dict, Any, Optional
from TTS.api import TTS
from app.models.tts.base_tts import BaseTTSService, TTSEngine
from app.core.logger import logger
from app.core.exceptions import TTSException


class CoquiTTSService(BaseTTSService):
    """
    Servicio Coqui TTS.
    Usa XTTS v2 para síntesis multilenguaje de alta calidad.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine_name = TTSEngine.COQUI
        self.model_name = config.get(
            "model",
            "tts_models/multilingual/multi-dataset/xtts_v2"
        )
        self.use_gpu = config.get("use_gpu", False)
        self.sample_rate = 24000
        self.tts = None

        # Rutas de audios de referencia para clonación
        from pathlib import Path
        self.voices_dir = Path(__file__).parent.parent.parent.parent / "voices"
        self.speaker_wavs = {
            "narradora": str(self.voices_dir / "narradora.wav"),
            "harry": str(self.voices_dir / "harry.wav")
        }

    async def initialize(self) -> bool:
        """Cargar modelo XTTS"""
        try:
            logger.info(f"Loading Coqui TTS model: {self.model_name}")

            # Cargar en thread separado para no bloquear
            loop = asyncio.get_event_loop()
            self.tts = await loop.run_in_executor(
                None,
                lambda: TTS(
                    model_name=self.model_name,
                    gpu=self.use_gpu
                )
            )

            self.is_ready = True
            logger.info("Coqui TTS initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Coqui initialization failed: {e}")
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
        Generar audio con Coqui XTTS.

        Args:
            text: Texto a sintetizar
            voice: Voz (narradora, harry)
            language: Código idioma (ca, ca-valencia)

        Returns:
            Audio PCM int16
        """
        if not self.is_ready or not self.tts:
            raise TTSException("Coqui service not initialized")

        if not text.strip():
            raise TTSException("Empty text")

        try:
            # XTTS usa código "ca" para catalán
            lang_code = "ca" if language.startswith("ca") else language

            # Determinar speaker o speaker_wav
            speaker_wav = self.speaker_wavs.get(voice.lower())

            # Verificar si el archivo existe, si no, usar speaker por defecto
            from pathlib import Path
            if speaker_wav and not Path(speaker_wav).exists():
                logger.warning(f"Reference wav not found: {speaker_wav}")
                speaker_wav = None

            # Ejecutar TTS en executor (blocking)
            loop = asyncio.get_event_loop()

            def run_tts():
                if speaker_wav:
                    return self.tts.tts(
                        text=text,
                        language=lang_code,
                        speaker_wav=speaker_wav
                    )
                else:
                    # Fallback a speaker genérico si no hay wav
                    speaker_name = voice if voice in getattr(self.tts, 'speakers', []) else None
                    if not speaker_name and not speaker_wav:
                        speaker_name = "Claribel Dervla" # Speaker por defecto de XTTS v2

                    return self.tts.tts(
                        text=text,
                        language=lang_code,
                        speaker=speaker_name
                    )

            wav = await loop.run_in_executor(None, run_tts)

            # Convertir a numpy array si no lo es
            if not isinstance(wav, np.ndarray):
                wav = np.array(wav)

            # Normalizar a int16
            wav_int16 = (wav * 32767).astype(np.int16)

            # Convertir a bytes
            buffer = io.BytesIO()
            sf.write(buffer, wav_int16, self.sample_rate, format='RAW', subtype='PCM_16')
            audio_bytes = buffer.getvalue()

            logger.info(f"Generated {len(audio_bytes)} bytes with Coqui ({voice})")
            return audio_bytes

        except Exception as e:
            logger.error(f"Coqui generation error: {e}")
            raise TTSException(f"Coqui error: {str(e)}")

    async def list_voices(self, language: Optional[str] = None) -> Dict[str, Any]:
        """Listar voces/speakers disponibles"""
        if not self.tts:
            return {"voices": []}

        try:
            # XTTS tiene speakers predefinidos
            speakers = getattr(self.tts, 'speakers', [])
            languages = getattr(self.tts, 'languages', [])

            return {
                "engine": "coqui",
                "model": self.model_name,
                "speakers": speakers if speakers else ["female", "male"],
                "languages": languages if languages else ["ca", "es", "en"]
            }
        except Exception as e:
            logger.error(f"Error listing Coqui voices: {e}")
            return {"voices": []}

    async def health_check(self) -> bool:
        """Health check"""
        if not self.is_ready or not self.tts:
            return False

        try:
            await self.generate_speech("Prova", voice="narradora")
            return True
        except Exception:
            return False

    async def shutdown(self):
        """Liberar memoria del modelo"""
        if self.tts:
            del self.tts
            self.tts = None
            logger.info("Coqui TTS unloaded")
