from __future__ import annotations

import logging
from typing import Callable, Any

from app.core.celery_settings import get_celery_config

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    celery_available = True
except Exception:
    Celery = None
    celery_available = False


def _noop_task_decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
    return fn


if celery_available and Celery is not None:
    config = get_celery_config()
    app = Celery("bioloupe", broker=config["broker_url"], backend=config["result_backend"])
    app.conf.update(config)

    # Wire beat schedule if available
    try:
        from app.worker.beat_schedule import get_beat_schedule
        app.conf.beat_schedule = get_beat_schedule()
    except Exception:
        # ignore if beat schedule cannot be imported in test env
        pass

    def task_decorator(**kwargs):
        return app.task(**kwargs)
else:
    class _DummyApp:
        def __init__(self):
            self.conf = {}

        def task(self, **kwargs):
            def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn
            return deco

    app = _DummyApp()

    def task_decorator(**kwargs):
        return _noop_task_decorator


def get_celery_app():
    return app


def get_task_decorator():
    return task_decorator
