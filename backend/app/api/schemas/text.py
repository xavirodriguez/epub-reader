"""
Schemas para procesamiento de texto.
"""
from pydantic import Field
from typing import List, Optional, Literal
from app.models.base import BaseSchema


class TextSegment(BaseSchema):
    """Segmento de texto con speaker"""
    speaker: str
    text: str
    original_text: Optional[str] = None


class ProcessTextRequest(BaseSchema):
    """Request para procesar texto"""
    text: str = Field(..., min_length=1)
    detect_speakers: bool = Field(default=True)
    dialect: str = Field(default="català", pattern="^(català|valencià)$")


class ProcessTextResponse(BaseSchema):
    """Response de procesamiento"""
    processed_segments: List[TextSegment]
    dialect: str
    metadata: dict


class ChapterExportRequest(BaseSchema):
    """Request para exportar capítulo completo"""
    chapter_text: str = Field(..., min_length=1)
    voice_narradora: str = Field(default="narradora")
    voice_harry: str = Field(default="harry")
    language: str = Field(default="ca")
    dialect: str = Field(default="català")
    engine: Optional[str] = None


class ChapterExportResponse(BaseSchema):
    """Response de exportación de capítulo"""
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    estimated_time_seconds: Optional[int] = None
