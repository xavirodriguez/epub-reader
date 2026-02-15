"""
Tareas asíncronas para Celery.
"""
import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Any
import numpy as np

from celery import Task
from app.workers.celery_app import celery_app
from app.core.logger import logger
from app.models.tts.tts_manager import tts_manager
from app.models.llm.text_processor import text_processor
from app.utils.audio import create_wav_file
from app.config import settings


class CallbackTask(Task):
    """
    Task base que inicializa servicios async.
    """
    _initialized = False

    def __call__(self, *args, **kwargs):
        if not self._initialized:
            # Inicializar servicios en el worker
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Inicializar TTS manager
            loop.run_until_complete(tts_manager.initialize())

            # Inicializar LLM
            from app.models.llm.ollama_service import ollama_service
            loop.run_until_complete(ollama_service.initialize())

            # Inicializar cache
            from app.core.cache import cache_manager
            loop.run_until_complete(cache_manager.connect())

            self._initialized = True
            logger.info("Celery worker services initialized")

        return self.run(*args, **kwargs)


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.workers.tasks.export_chapter_task",
    max_retries=3
)
def export_chapter_task(
    self,
    chapter_text: str,
    voice_narradora: str = "narradora",
    voice_harry: str = "harry",
    language: str = "ca",
    dialect: str = "català",
    engine: str = None
) -> Dict[str, Any]:
    """
    Tarea para exportar capítulo completo como WAV.

    Proceso:
    1. Procesar texto (detectar speakers, dialecto)
    2. Dividir en chunks
    3. Generar audio para cada chunk
    4. Concatenar en WAV
    5. Guardar archivo

    Args:
        self: Celery task instance
        chapter_text: Texto del capítulo
        voice_narradora: Voz para narraciones
        voice_harry: Voz para Harry
        language: Código de idioma
        dialect: Dialecto
        engine: Engine TTS específico

    Returns:
        Dict con file_path y metadata
    """
    logger.info(f"Starting chapter export task: {self.request.id}")

    try:
        loop = asyncio.get_event_loop()

        # 1. Procesar texto
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "message": "Procesando texto..."}
        )

        processed = loop.run_until_complete(
            text_processor.process_chapter_text(
                text=chapter_text,
                detect_speakers=True,
                dialect=dialect
            )
        )

        segments = processed["processed_segments"]

        # 2. Preparar para TTS (dividir segmentos largos)
        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "message": "Preparando segmentos..."}
        )

        tts_segments = loop.run_until_complete(
            text_processor.prepare_for_tts(segments, max_length=1000)
        )

        total_segments = len(tts_segments)
        logger.info(f"Processing {total_segments} TTS segments")

        # 3. Generar audio para cada segmento
        audio_chunks = []

        for i, segment in enumerate(tts_segments):
            # Seleccionar voz según speaker
            if segment["speaker"].lower() == "harry":
                voice = voice_harry
            else:
                voice = voice_narradora

            # Update progress
            progress = 10 + int((i / total_segments) * 80)
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": progress,
                    "total": 100,
                    "message": f"Generando audio {i+1}/{total_segments}..."
                }
            )

            # Generar audio
            try:
                audio_bytes, source = loop.run_until_complete(
                    tts_manager.generate_speech(
                        text=segment["text"],
                        voice=voice,
                        language=language,
                        engine=engine
                    )
                )

                # Convertir bytes a numpy array (int16)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_chunks.append(audio_array)

                logger.info(
                    f"Segment {i+1}/{total_segments} generated "
                    f"({len(audio_bytes)} bytes, source: {source})"
                )

                # Delay entre requests (evitar rate limits)
                if source != "cache":
                    time.sleep(1)  # Reducido de 15s para propósitos de prueba/demo si es necesario, pero el prompt decía 15.
                    # El prompt decía time.sleep(15) # 15 segundos entre generaciones
                    # Lo dejaré en 15 como dice el prompt.
                    time.sleep(14)

            except Exception as e:
                logger.error(f"Error generating segment {i+1}: {e}")
                # Continuar con siguiente segmento
                continue

        if not audio_chunks:
            raise Exception("No audio was generated successfully")

        # 4. Concatenar audio
        self.update_state(
            state="PROGRESS",
            meta={"current": 95, "total": 100, "message": "Concatenando audio..."}
        )

        combined_audio = np.concatenate(audio_chunks)

        # 5. Crear archivo WAV
        output_dir = Path("/tmp/epub_narrator_exports")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"chapter_{self.request.id}.wav"

        create_wav_file(
            audio_data=combined_audio,
            output_path=str(output_file),
            sample_rate=settings.TTS_SAMPLE_RATE
        )

        file_size = output_file.stat().st_size
        duration = len(combined_audio) / settings.TTS_SAMPLE_RATE

        logger.info(
            f"Chapter export completed: {output_file} "
            f"({file_size/1024/1024:.2f} MB, {duration:.1f}s)"
        )

        return {
            "file_path": str(output_file),
            "file_size_bytes": file_size,
            "duration_seconds": duration,
            "segments_processed": total_segments,
            "sample_rate": settings.TTS_SAMPLE_RATE
        }

    except Exception as e:
        logger.error(f"Chapter export failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="app.workers.tasks.cleanup_old_exports")
def cleanup_old_exports():
    """
    Tarea periódica para limpiar exports antiguos.
    Se ejecuta cada hora vía Celery Beat.
    """
    logger.info("Starting cleanup of old exports")

    try:
        export_dir = Path("/tmp/epub_narrator_exports")

        if not export_dir.exists():
            return {"deleted": 0}

        # Eliminar archivos de más de 2 horas
        max_age = 2 * 3600  # 2 horas en segundos
        now = time.time()
        deleted = 0

        for file_path in export_dir.glob("*.wav"):
            file_age = now - file_path.stat().st_mtime

            if file_age > max_age:
                try:
                    file_path.unlink()
                    deleted += 1
                    logger.info(f"Deleted old export: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")

        logger.info(f"Cleanup completed: {deleted} files deleted")
        return {"deleted": deleted}

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {"error": str(e)}
