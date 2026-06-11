"""Celery application — workers for OCR, enrichment, search (M2+)."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("bschat", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"

# M6 Layer 2 — daily stale auto-refresh scan (Pro users with auto_refresh ON).
celery_app.conf.beat_schedule = {
    "stale-company-refresh-daily": {
        "task": "companies.stale_scan",
        "schedule": 24 * 60 * 60,
    },
}

celery_app.autodiscover_tasks(["app.workers.tasks"])
