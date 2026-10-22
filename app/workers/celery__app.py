
"""Celery application for EnergyMax production tasks."""

from celery import Celery
from app.core.config import settings


if not settings.REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is required to run the Celery worker. "
        "Configure it in the production environment."
    )
celery_app = Celery(
    "energymax",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    task_soft_time_limit=240,
    task_time_limit=300,
)
