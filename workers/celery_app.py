import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "meetingos",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.tasks.ingestion",
        "workers.tasks.sync",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "meetingos.asr": {"exchange": "meetingos.asr", "routing_key": "meetingos.asr"},
        "meetingos.nlp": {"exchange": "meetingos.nlp", "routing_key": "meetingos.nlp"},
        "meetingos.embedding": {
            "exchange": "meetingos.embedding",
            "routing_key": "meetingos.embedding",
        },
        "meetingos.sync": {"exchange": "meetingos.sync", "routing_key": "meetingos.sync"},
    },
    task_routes={
        "workers.tasks.ingestion.*": {"queue": "meetingos.asr"},
        "workers.tasks.sync.*": {"queue": "meetingos.sync"},
    },
)
