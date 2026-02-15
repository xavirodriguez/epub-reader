"""
Schemas para procesamiento de texto.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class TextSegment(BaseModel):
    """Segmento de texto con speaker"""
    speaker: str
    text: str
    original_text: Optional[str] = None


class ProcessTextRequest(BaseModel):
    """Request para procesar texto"""
    text: str = Field(..., min_length=1)
    detect_speakers: bool = Field(default=True)
    dialect: str = Field(default="català", pattern="^(català|valencià)$")


class ProcessTextResponse(BaseModel):
    """Response de procesamiento"""
    processed_segments: List[TextSegment]
    dialect: str
    metadata: dict


class ChapterExportRequest(BaseModel):
    """Request para exportar capítulo completo"""
    chapter_text: str = Field(..., min_length=1)
    voice_narradora: str = Field(default="narradora")
    voice_harry: str = Field(default="harry")
    language: str = Field(default="ca")
    dialect: str = Field(default="català")
    engine: Optional[str] = None


class ChapterExportResponse(BaseModel):
    """Response de exportación de capítulo"""
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    estimated_time_seconds: Optional[int] = None
