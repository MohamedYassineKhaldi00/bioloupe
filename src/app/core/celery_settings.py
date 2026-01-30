from __future__ import annotations

import os
from typing import Dict, Any
from app.core.config import get_settings


def get_celery_config() -> Dict[str, Any]:
    settings = get_settings()
    broker = settings.redis_url
    return {
        "broker_url": broker,
        "result_backend": broker,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "result_expires": 60 * 60 * 24,  # 24 hours
        "worker_concurrency": int(os.getenv("WORKER_CONCURRENCY", "4")),
        "task_soft_time_limit": int(os.getenv("TASK_SOFT_TIME_LIMIT", "300")),
        "task_time_limit": int(os.getenv("TASK_TIME_LIMIT", "600")),
    }
