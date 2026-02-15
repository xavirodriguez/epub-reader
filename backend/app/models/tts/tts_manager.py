"""
Manager principal de TTS.
Orquesta múltiples engines, fallbacks automáticos y selección inteligente.
"""
import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum

from app.models.tts.base_tts import BaseTTSService, TTSEngine
from app.models.tts.piper_service import PiperTTSService
from app.models.tts.coqui_service import CoquiTTSService
from app.models.tts.bark_service import BarkTTSService
from app.core.logger import logger
from app.core.exceptions import TTSException, ServiceUnavailableException
from app.core.cache import cache_manager, cached
from app.config import settings


class TTSManager:
    """
    Gestor centralizado de servicios TTS.

    Responsabilidades:
    - Inicializar múltiples engines
    - Seleccionar engine óptimo según contexto
    - Fallback automático si un engine falla
    - Cachear resultados
    - Health monitoring
    """

    def __init__(self):
        self.engines: Dict[TTSEngine, BaseTTSService] = {}
        self.default_engine = TTSEngine(settings.DEFAULT_TTS_ENGINE)
        self.fallback_order = [
            TTSEngine.PIPER,    # Rápido y confiable
            TTSEngine.COQUI,    # Calidad media-alta
            TTSEngine.BARK,     # Calidad máxima pero lento
        ]
        self.initialized = False

    async def initialize(self):
        """
        Inicializar todos los engines TTS configurados.
        Los engines que fallen se desactivan pero no bloquean el startup.
        """
        logger.info("Initializing TTS Manager...")

        # Configuraciones por engine
        engines_config = {
            TTSEngine.PIPER: {
                "binary_path": settings.PIPER_BINARY_PATH,
                "model_path": settings.PIPER_MODEL_PATH,
                "sample_rate": settings.TTS_SAMPLE_RATE
            },
            TTSEngine.COQUI: {
                "model": settings.COQUI_MODEL,
                "use_gpu": settings.COQUI_USE_GPU,
            },
            TTSEngine.BARK: {
                "use_gpu": settings.BARK_USE_GPU,
                "small_models": settings.BARK_SMALL_MODELS
            }
        }

        # Inicializar engines en paralelo
        init_tasks = []

        for engine_type, config in engines_config.items():
            task = self._init_engine(engine_type, config)
            init_tasks.append(task)

        # Esperar a todas las inicializaciones
        results = await asyncio.gather(*init_tasks, return_exceptions=True)

        # Reportar resultados
        active_engines = [
            engine for engine, service in self.engines.items()
            if service.is_ready
        ]

        if not active_engines:
            logger.error("No TTS engines available!")
            raise ServiceUnavailableException("TTS")

        logger.info(f"TTS Manager ready with engines: {[e.value for e in active_engines]}")
        self.initialized = True

    async def _init_engine(
        self,
        engine_type: TTSEngine,
        config: Dict[str, Any]
    ):
        """Inicializar un engine específico"""
        try:
            # Crear instancia según tipo
            if engine_type == TTSEngine.PIPER:
                service = PiperTTSService(config)
            elif engine_type == TTSEngine.COQUI:
                service = CoquiTTSService(config)
            elif engine_type == TTSEngine.BARK:
                service = BarkTTSService(config)
            else:
                logger.warning(f"Unknown engine type: {engine_type}")
                return

            # Inicializar
            success = await service.initialize()

            if success:
                self.engines[engine_type] = service
                logger.info(f"✓ {engine_type.value} TTS ready")
            else:
                logger.warning(f"✗ {engine_type.value} TTS failed to initialize")

        except Exception as e:
            logger.error(f"Error initializing {engine_type.value}: {e}")

    async def generate_speech(
        self,
        text: str,
        voice: str = "narradora",
        language: str = "ca",
        engine: Optional[TTSEngine] = None,
        use_cache: bool = True
    ) -> tuple[bytes, str]:
        """
        Generar audio con el engine especificado o el por defecto.
        Incluye fallback automático.

        Args:
            text: Texto a sintetizar
            voice: Voz a usar
            language: Código de idioma
            engine: Engine específico (None = usar default)
            use_cache: Usar caché si disponible

        Returns:
            Tuple (audio_bytes, engine_used)

        Raises:
            TTSException: Si todos los engines fallan
        """
        if not self.initialized:
            raise TTSException("TTS Manager not initialized")

        # Validar longitud de texto
        if len(text) > settings.MAX_TEXT_LENGTH:
            raise TTSException(
                f"Text too long ({len(text)} chars, max {settings.MAX_TEXT_LENGTH})"
            )

        # Generar clave de caché
        if use_cache and settings.TTS_CACHE_ENABLED:
            cache_key = cache_manager._generate_key(
                prefix="tts",
                text=text[:100],  # Hash de primeros 100 chars
                voice=voice,
                language=language
            )

            # Intentar obtener de caché
            cached_audio = await cache_manager.get(cache_key)
            if cached_audio:
                logger.info("Audio retrieved from cache")
                return cached_audio, "cache"

        # Determinar orden de engines a intentar
        target_engine = engine or self.default_engine

        if target_engine in self.engines:
            engines_to_try = [target_engine] + [
                e for e in self.fallback_order if e != target_engine
            ]
        else:
            engines_to_try = self.fallback_order

        # Intentar generación con cada engine
        last_error = None

        for engine_type in engines_to_try:
            if engine_type not in self.engines:
                continue

            service = self.engines[engine_type]

            if not service.is_ready:
                continue

            try:
                logger.info(f"Generating speech with {engine_type.value}")

                audio_bytes = await service.generate_speech(
                    text=text,
                    voice=voice,
                    language=language
                )

                # Convertir a WAV para compatibilidad universal
                from app.utils.audio import get_wav_bytes, pcm_to_numpy
                audio_array = pcm_to_numpy(audio_bytes)
                audio_bytes = get_wav_bytes(audio_array, sample_rate=settings.TTS_SAMPLE_RATE)

                # Guardar en caché
                if use_cache and settings.TTS_CACHE_ENABLED:
                    await cache_manager.set(cache_key, audio_bytes)

                logger.info(
                    f"Successfully generated {len(audio_bytes)} bytes "
                    f"with {engine_type.value}"
                )

                return audio_bytes, engine_type.value

            except Exception as e:
                logger.error(f"{engine_type.value} generation failed: {e}")
                last_error = e
                continue

        # Todos los engines fallaron
        error_msg = f"All TTS engines failed. Last error: {last_error}"
        logger.error(error_msg)
        raise TTSException(error_msg)

    async def list_all_voices(self) -> Dict[str, Any]:
        """Listar voces disponibles de todos los engines"""
        all_voices = {}

        for engine_type, service in self.engines.items():
            if service.is_ready:
                try:
                    voices = await service.list_voices()
                    all_voices[engine_type.value] = voices
                except Exception as e:
                    logger.error(f"Error listing voices for {engine_type}: {e}")

        return all_voices

    async def health_check(self) -> Dict[str, bool]:
        """Verificar salud de todos los engines"""
        health = {}

        for engine_type, service in self.engines.items():
            try:
                is_healthy = await service.health_check()
                health[engine_type.value] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {engine_type}: {e}")
                health[engine_type.value] = False

        return health

    async def shutdown(self):
        """Apagar todos los engines"""
        logger.info("Shutting down TTS Manager...")

        for engine_type, service in self.engines.items():
            try:
                await service.shutdown()
                logger.info(f"✓ {engine_type.value} shut down")
            except Exception as e:
                logger.error(f"Error shutting down {engine_type}: {e}")

        self.initialized = False


# Singleton global
tts_manager = TTSManager()
