"""Celery application shared by the API (producer) and the worker (consumer)."""
from celery import Celery

from .settings import settings

celery_app = Celery(
    "churnmod",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks.train_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    task_acks_late=False,
)

app = celery_app
