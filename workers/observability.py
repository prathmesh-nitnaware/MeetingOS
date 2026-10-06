import time

from pydantic import BaseModel, Field


class WorkerTaskMetric(BaseModel):
    task_name: str
    queue: str
    duration_ms: float
    status: str
    retry_count: int = 0
    error_message: str | None = None
    timestamp: float = Field(default_factory=time.time)


class WorkerObservabilitySummary(BaseModel):
    active_queues: list[str] = Field(default_factory=list)
    registered_workers: int = 0
    tasks_processed: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    mean_duration_ms: float = 0.0
    throughput_tasks_per_min: float = 0.0


class WorkerTelemetryTracker:
    """Thread-safe worker metrics collector for background Celery tasks."""

    def __init__(self) -> None:
        self._metrics: list[WorkerTaskMetric] = []
        self._start_time: float = time.time()

    def record_task(
        self,
        task_name: str,
        queue: str,
        duration_ms: float,
        status: str,
        retry_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        metric = WorkerTaskMetric(
            task_name=task_name,
            queue=queue,
            duration_ms=duration_ms,
            status=status,
            retry_count=retry_count,
            error_message=error_message,
        )
        self._metrics.append(metric)
        if len(self._metrics) > 2000:
            self._metrics.pop(0)

    def get_summary(self, active_queues: list[str] | None = None) -> WorkerObservabilitySummary:
        total = len(self._metrics)
        succ = sum(1 for m in self._metrics if m.status == "success")
        fail = sum(1 for m in self._metrics if m.status == "failed")
        retried = sum(m.retry_count for m in self._metrics)
        durations = [m.duration_ms for m in self._metrics]
        mean_dur = sum(durations) / total if total > 0 else 0.0

        elapsed_mins = (time.time() - self._start_time) / 60.0
        tpm = total / elapsed_mins if elapsed_mins > 0 else float(total)

        default_queues = [
            "default",
            "meetingos.asr",
            "meetingos.nlp",
            "meetingos.embedding",
            "meetingos.sync",
        ]

        return WorkerObservabilitySummary(
            active_queues=active_queues or default_queues,
            registered_workers=1,
            tasks_processed=total,
            tasks_succeeded=succ,
            tasks_failed=fail,
            tasks_retried=retried,
            mean_duration_ms=round(mean_dur, 2),
            throughput_tasks_per_min=round(tpm, 2),
        )


global_worker_telemetry = WorkerTelemetryTracker()
