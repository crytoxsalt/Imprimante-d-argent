from celery import Celery
from ..config import settings

celery = Celery(
    "cashroll",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["web.backend.tasks.generate", "web.backend.tasks.upload"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_routes={
        "web.backend.tasks.generate.*": {"queue": "generation"},
        "web.backend.tasks.upload.*": {"queue": "uploads"},
    },
)
