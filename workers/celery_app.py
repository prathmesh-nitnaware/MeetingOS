from apps.api.config import settings
from celery import Celery
from kombu import Queue

# Queue names. Routes below MUST match the explicit task names (``@task(name=...)``);
# glob patterns on module paths never matched those names, so every task silently went
# to a "celery" queue that no worker consumed.
QUEUE_DEFAULT = "default"
QUEUE_ASR = "meetingos.asr"
QUEUE_NLP = "meetingos.nlp"
QUEUE_EMBEDDING = "meetingos.embedding"
QUEUE_SYNC = "meetingos.sync"
ALL_QUEUES = [QUEUE_DEFAULT, QUEUE_ASR, QUEUE_NLP, QUEUE_EMBEDDING, QUEUE_SYNC]

celery_app = Celery(
    "meetingos",
    # Read from settings (and therefore .env), not only from OS environment variables
    broker=settings.broker_url,
    backend=settings.result_backend_url,
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
    task_default_queue=QUEUE_DEFAULT,
    # Each queue needs its own routing key: without one they all share the default key
    # and every task is copied to every queue (and processed once per queue).
    task_queues=[Queue(name, routing_key=name) for name in ALL_QUEUES],
    task_routes={
        "tasks.process_meeting_ingestion": {"queue": QUEUE_ASR},
        "tasks.sync_connector": {"queue": QUEUE_SYNC},
    },
    # Fail fast when the broker is unreachable instead of hanging the API request for minutes
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 1,
    },
    broker_connection_timeout=3,
    broker_connection_retry_on_startup=True,
    result_expires=24 * 3600,
)
