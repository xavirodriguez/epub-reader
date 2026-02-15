"""
Procesador de texto de alto nivel.
Combina servicios LLM para operaciones complejas.
"""
from typing import List, Dict, Any
from app.models.llm.ollama_service import ollama_service
from app.core.logger import logger
from app.config import settings


class TextProcessor:
    """
    Procesador de texto que orquesta servicios LLM.
    """

    def __init__(self):
        self.llm = ollama_service
        self.max_chunk_size = settings.CHUNK_SIZE

    async def process_chapter_text(
        self,
        text: str,
        detect_speakers: bool = True,
        dialect: str = "català"
    ) -> Dict[str, Any]:
        """
        Procesar texto completo de un capítulo.

        Args:
            text: Texto del capítulo
            detect_speakers: Si detectar speakers
            dialect: Dialecto objetivo

        Returns:
            Dict con texto procesado y metadata
        """
        result = {
            "original_text": text,
            "processed_segments": [],
            "dialect": dialect,
            "metadata": {
                "char_count": len(text),
                "speakers_detected": False
            }
        }

        try:
            # 1. Detectar speakers si es necesario
            if detect_speakers:
                segments_data = await self.llm.detect_speakers(text)
                segments = segments_data.get("segments", [])
                result["metadata"]["speakers_detected"] = True
                result["metadata"]["segment_count"] = len(segments)
            else:
                # Todo como narración
                segments = [{"speaker": "Narradora", "text": text}]

            # 2. Adaptar dialecto si no es estándar
            if dialect.lower() in ["valencià", "valenciano"]:
                processed_segments = []
                for segment in segments:
                    adapted_text = await self.llm.translate_dialect(
                        segment["text"],
                        target_dialect="valencià"
                    )
                    processed_segments.append({
                        "speaker": segment["speaker"],
                        "text": adapted_text,
                        "original_text": segment["text"]
                    })
                result["processed_segments"] = processed_segments
            else:
                result["processed_segments"] = segments

            logger.info(
                f"Processed chapter: {len(segments)} segments, "
                f"dialect: {dialect}"
            )

            return result

        except Exception as e:
            logger.error(f"Chapter processing error: {e}")
            # Fallback: retornar original sin procesar
            result["processed_segments"] = [{
                "speaker": "Narradora",
                "text": text
            }]
            result["error"] = str(e)
            return result

    async def prepare_for_tts(
        self,
        segments: List[Dict[str, Any]],
        max_length: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Preparar segmentos para TTS dividiendo texto largo.

        Args:
            segments: Lista de segmentos con speaker y text
            max_length: Longitud máxima por chunk

        Returns:
            Lista de segmentos listos para TTS
        """
        prepared = []

        for segment in segments:
            text = segment["text"]
            speaker = segment["speaker"]

            if len(text) <= max_length:
                prepared.append(segment)
            else:
                # Dividir en chunks
                chunks = await self.llm.chunk_text_intelligently(
                    text,
                    max_chunk_size=max_length
                )

                for chunk in chunks:
                    prepared.append({
                        "speaker": speaker,
                        "text": chunk
                    })

        logger.info(f"Prepared {len(prepared)} TTS-ready segments")
        return prepared


# Singleton
text_processor = TextProcessor()
