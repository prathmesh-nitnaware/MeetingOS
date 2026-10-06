import subprocess
import sys
from pathlib import Path

from workers.celery_app import celery_app
from workers.observability import WorkerTelemetryTracker


def test_celery_queues_and_routing():
    import workers.tasks.ingestion  # noqa: F401  (registers the tasks)
    import workers.tasks.sync  # noqa: F401

    queue_names = {q.name for q in celery_app.conf.task_queues}
    assert {
        "default",
        "meetingos.asr",
        "meetingos.nlp",
        "meetingos.embedding",
        "meetingos.sync",
    } <= queue_names
    assert celery_app.conf.task_default_queue == "default"

    # Routing must resolve for the actual registered task names
    router = celery_app.amqp.router
    assert router.route({}, "tasks.process_meeting_ingestion")["queue"].name == "meetingos.asr"
    assert router.route({}, "tasks.sync_connector")["queue"].name == "meetingos.sync"

    # Queues sharing a routing key on the same exchange would each get a copy of every task
    bindings = [(q.exchange.name, q.routing_key) for q in celery_app.amqp.queues.values()]
    assert len(bindings) == len(set(bindings))


def test_worker_app_imports_in_a_fresh_interpreter():
    # `celery -A workers.celery_app worker` imports this module first; a circular
    # import there only shows up in a clean process, not inside the test session.
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "import workers.celery_app, workers.tasks"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


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


def test_job_errors_hide_internal_details():
    from packages.speech.whisper import AudioDecodeError
    from workers.tasks.ingestion import _friendly_error

    assert _friendly_error(AudioDecodeError("The uploaded file has no audio track.")) == (
        "The uploaded file has no audio track."
    )
    internal = _friendly_error(RuntimeError("connection to 10.0.0.5:5432 refused"))
    assert "10.0.0.5" not in internal
    assert "internal error" in internal
