from __future__ import annotations

import os

from redis import Redis
from rq import Queue, Retry


def get_analysis_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    return Queue(
        "trademark-analysis",
        connection=connection,
        default_timeout=int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "3600")),
    )


def enqueue_analysis(job_id: str) -> str:
    queue = get_analysis_queue()
    queued = queue.enqueue(
        "app.worker.process_analysis_job",
        job_id,
        retry=Retry(max=3, interval=[15, 60, 180]),
        result_ttl=86400,
        failure_ttl=604800,
    )
    return queued.id
