import time
from typing import Any
from app.workers.celery_app import celery_app


@celery_app.task(name="system.ping_worker", bind=True)
def ping_worker(self: Any) -> dict[str, Any]:
    """Diagnostic task verifying Celery worker execution, host resolution, and queue readiness."""
    return {
        "status": "pong",
        "task_id": self.request.id,
        "timestamp": time.time(),
        "worker": self.request.hostname or "unknown",
        "message": "DEVA Intelligence worker is active and accepting tasks.",
    }
