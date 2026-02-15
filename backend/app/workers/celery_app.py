"""
Configuración de Celery para tareas asíncronas.
"""
from celery import Celery
from app.config import settings

# Crear instancia Celery
celery_app = Celery(
    "epub_narrator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Configuración
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarea
    task_soft_time_limit=3300,  # Warning a los 55 min
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Configuración de resultados
celery_app.conf.result_expires = 3600  # Resultados expiran en 1h
celery_app.conf.result_persistent = True

# Beat schedule (tareas periódicas)
celery_app.conf.beat_schedule = {
    "cleanup-old-exports": {
        "task": "app.workers.tasks.cleanup_old_exports",
        "schedule": 3600.0,  # Cada hora
    },
}
