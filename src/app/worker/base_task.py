from __future__ import annotations

import logging
from typing import Any

try:
    from celery import Task as CeleryTask
    celery_available = True
except Exception:
    CeleryTask = object
    celery_available = False

logger = logging.getLogger(__name__)


class BaseTask(CeleryTask if celery_available else object):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc: BaseException, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        logger.exception("Task failed: %s %s", task_id, exc)

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        logger.info("Task succeeded: %s", task_id)
