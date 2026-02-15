"""
Endpoints para exportación de capítulos completos.
Usa Celery para procesamiento asíncrono.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from typing import Optional

from app.api.schemas.text import (
    ChapterExportRequest,
    ChapterExportResponse
)
from app.workers.tasks import export_chapter_task
from app.core.logger import logger

router = APIRouter(prefix="/chapters", tags=["Chapters"])


@router.post("/export", response_model=ChapterExportResponse)
async def export_chapter(
    request: ChapterExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Exportar capítulo completo como archivo de audio.

    Proceso asíncrono:
    1. Detecta speakers en el texto
    2. Genera audio para cada segmento
    3. Concatena en un solo archivo WAV

    Returns task_id para consultar progreso
    """
    try:
        # Crear tarea Celery
        task = export_chapter_task.delay(
            chapter_text=request.chapter_text,
            voice_narradora=request.voice_narradora,
            voice_harry=request.voice_harry,
            language=request.language,
            dialect=request.dialect,
            engine=request.engine
        )

        # Estimar tiempo (muy aproximado)
        words = len(request.chapter_text.split())
        estimated_time = int(words * 0.5)  # ~0.5s por palabra

        logger.info(f"Chapter export task created: {task.id}")

        return ChapterExportResponse(
            task_id=task.id,
            status="queued",
            estimated_time_seconds=estimated_time
        )

    except Exception as e:
        logger.error(f"Failed to create export task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export error: {str(e)}"
        )


@router.get("/export/{task_id}/status")
async def get_export_status(task_id: str):
    """
    Consultar estado de exportación.

    - **task_id**: ID de la tarea

    Returns:
    - status: queued/processing/completed/failed
    - progress: porcentaje completado
    - result: URL de descarga si completado
    """
    from app.workers.celery_app import celery_app

    try:
        task = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task.state.lower(),
        }

        if task.state == "PROGRESS":
            response["progress"] = task.info.get("current", 0)
            response["total"] = task.info.get("total", 100)
            response["message"] = task.info.get("message", "")

        elif task.state == "SUCCESS":
            response["result"] = task.result
            response["download_url"] = f"/api/chapters/download/{task_id}"

        elif task.state == "FAILURE":
            response["error"] = str(task.info)

        return response

    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.get("/download/{task_id}")
async def download_chapter(task_id: str):
    """
    Descargar capítulo exportado.
    """
    from app.workers.celery_app import celery_app
    from fastapi.responses import FileResponse
    import os

    try:
        task = celery_app.AsyncResult(task_id)

        if task.state != "SUCCESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task not completed: {task.state}"
            )

        file_path = task.result.get("file_path")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=f"chapter_{task_id[:8]}.wav"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
