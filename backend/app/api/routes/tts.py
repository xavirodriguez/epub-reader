"""
Endpoints REST para TTS.
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
import base64

from app.api.schemas.tts import (
    TTSRequest,
    TTSResponse,
    EngineInfo,
    VoiceInfo
)
from app.models.tts.tts_manager import tts_manager
from app.core.logger import logger
from app.core.exceptions import TTSException

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("/generate", response_model=TTSResponse)
async def generate_tts(request: TTSRequest):
    """
    Generar audio TTS desde texto.

    - **text**: Texto a sintetizar (máx 5000 chars)
    - **voice**: Voz a usar (narradora, harry)
    - **language**: Idioma (ca, ca-valencia)
    - **engine**: Engine específico (opcional)
    - **use_cache**: Usar caché si disponible

    Returns audio en base64 (PCM int16, 24kHz)
    """
    try:
        audio_bytes, source = await tts_manager.generate_speech(
            text=request.text,
            voice=request.voice,
            language=request.language,
            engine=request.engine,
            use_cache=request.use_cache
        )

        # Codificar a base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        # Calcular duración aproximada
        # PCM int16 = 2 bytes per sample
        sample_rate = 24000
        num_samples = len(audio_bytes) // 2
        duration = num_samples / sample_rate

        return TTSResponse(
            audio_data=audio_base64,
            source=source,
            cached=(source == "cache"),
            sample_rate=sample_rate,
            duration_seconds=round(duration, 2)
        )

    except TTSException as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/voices", response_model=list[EngineInfo])
async def list_voices():
    """
    Listar todas las voces disponibles de todos los engines.
    """
    try:
        all_voices = await tts_manager.list_all_voices()

        engines_info = []
        for engine_name, voices_data in all_voices.items():
            # Convertir a formato estándar
            voices = []

            if isinstance(voices_data.get('voices'), dict):
                for voice_name, voice_info in voices_data['voices'].items():
                    voices.append(VoiceInfo(
                        name=voice_name,
                        gender=voice_info.get('gender'),
                        language='ca',
                        description=voice_info.get('description')
                    ))

            engines_info.append(EngineInfo(
                engine=engine_name,
                ready=True,
                voices=voices
            ))

        return engines_info

    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list voices"
        )


@router.get("/engines/status")
async def engines_status():
    """
    Estado de todos los engines TTS.
    """
    try:
        health = await tts_manager.health_check()

        return {
            "engines": health,
            "default_engine": tts_manager.default_engine.value,
            "fallback_order": [e.value for e in tts_manager.fallback_order]
        }

    except Exception as e:
        logger.error(f"Error checking engines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check engines"
        )
