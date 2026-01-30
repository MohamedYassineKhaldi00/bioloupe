from app.worker.celery_config import CELERY_TASK_ROUTES, CELERYBEAT_SCHEDULE


def test_routes_defined():
    assert 'app.worker.tasks.embedding_tasks.*' in CELERY_TASK_ROUTES
    assert 'app.worker.tasks.indexing_tasks.*' in CELERY_TASK_ROUTES


def test_beat_schedule_defined():
    assert 'daily-publication-indexing' in CELERYBEAT_SCHEDULE
    sched = CELERYBEAT_SCHEDULE['daily-publication-indexing']
    assert 'task' in sched
    assert 'schedule' in sched
