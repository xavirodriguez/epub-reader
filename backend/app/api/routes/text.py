"""
Endpoints para procesamiento de texto.
"""
from fastapi import APIRouter, HTTPException, status

from app.api.schemas.text import (
    ProcessTextRequest,
    ProcessTextResponse,
    TextSegment
)
from app.models.llm.text_processor import text_processor
from app.core.logger import logger

router = APIRouter(prefix="/text", tags=["Text Processing"])


@router.post("/process", response_model=ProcessTextResponse)
async def process_text(request: ProcessTextRequest):
    """
    Procesar texto: detectar speakers y adaptar dialecto.

    - **text**: Texto a procesar
    - **detect_speakers**: Si detectar narradora/personajes
    - **dialect**: Dialecto objetivo (català, valencià)

    Returns texto segmentado por speaker
    """
    try:
        result = await text_processor.process_chapter_text(
            text=request.text,
            detect_speakers=request.detect_speakers,
            dialect=request.dialect
        )

        # Convertir a schema
        segments = [
            TextSegment(**segment)
            for segment in result["processed_segments"]
        ]

        return ProcessTextResponse(
            processed_segments=segments,
            dialect=result["dialect"],
            metadata=result["metadata"]
        )

    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing error: {str(e)}"
        )


@router.post("/chunk")
async def chunk_text(text: str, max_size: int = 1000):
    """
    Dividir texto en chunks inteligentes.

    - **text**: Texto a dividir
    - **max_size**: Tamaño máximo por chunk
    """
    try:
        from app.models.llm.ollama_service import ollama_service

        chunks = await ollama_service.chunk_text_intelligently(
            text=text,
            max_chunk_size=max_size
        )

        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "original_length": len(text)
        }

    except Exception as e:
        logger.error(f"Text chunking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
