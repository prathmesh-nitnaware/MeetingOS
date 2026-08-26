from workers.celery_app import celery_app
from workers.observability import WorkerTelemetryTracker


def test_celery_queues_and_routing():
    queues = celery_app.conf.task_queues
    assert queues is not None
    assert "meetingos.asr" in queues
    assert "meetingos.nlp" in queues
    assert "meetingos.embedding" in queues
    assert "meetingos.sync" in queues

    routes = celery_app.conf.task_routes
    assert routes is not None
    assert routes["workers.tasks.ingestion.*"]["queue"] == "meetingos.asr"
    assert routes["workers.tasks.sync.*"]["queue"] == "meetingos.sync"


def test_worker_telemetry_tracker():
    tracker = WorkerTelemetryTracker()
    tracker.record_task(
        task_name="workers.tasks.ingestion.run_ingestion_pipeline",
        queue="meetingos.asr",
        duration_ms=45.2,
        status="success",
    )
    tracker.record_task(
        task_name="workers.tasks.sync.sync_teams",
        queue="meetingos.sync",
        duration_ms=120.0,
        status="failed",
        error_message="Tenant timeout",
    )

    summary = tracker.get_summary()
    assert summary.tasks_processed == 2
    assert summary.tasks_succeeded == 1
    assert summary.tasks_failed == 1
    assert summary.mean_duration_ms > 0
    assert "meetingos.asr" in summary.active_queues
