"""
Schemas Pydantic para endpoints TTS.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from app.models.tts.base_tts import TTSEngine


class TTSRequest(BaseModel):
    """Request para generación TTS"""
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="narradora", description="Voice name")
    language: str = Field(default="ca", pattern="^(ca|ca-valencia|es|en)$")
    engine: Optional[TTSEngine] = Field(default=None, description="Specific engine")
    use_cache: bool = Field(default=True)

    @field_validator('text')
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Limpiar y validar texto"""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Text cannot be empty")
        return cleaned


class TTSResponse(BaseModel):
    """Response de generación TTS"""
    audio_data: str = Field(..., description="Base64 encoded PCM audio")
    source: str = Field(..., description="Source: cache/piper/coqui/bark/gemini")
    cached: bool = Field(default=False)
    sample_rate: int = Field(default=24000)
    duration_seconds: Optional[float] = None


class VoiceInfo(BaseModel):
    """Información de una voz"""
    name: str
    gender: Optional[str] = None
    language: str
    description: Optional[str] = None


class EngineInfo(BaseModel):
    """Información de un engine TTS"""
    engine: str
    ready: bool
    voices: list[VoiceInfo] = []


class HealthCheckResponse(BaseModel):
    """Response de health check"""
    status: Literal["healthy", "degraded", "unhealthy"]
    engines: dict[str, bool]
    cache_available: bool
    llm_available: bool
