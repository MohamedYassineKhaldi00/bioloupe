from __future__ import annotations

CELERY_TASK_ROUTES = {
    'app.worker.tasks.embedding_tasks.*': {'queue': 'embeddings'},
    'app.worker.tasks.indexing_tasks.*': {'queue': 'indexing'},
    'app.worker.tasks.notification_tasks.*': {'queue': 'notifications'},
    'app.worker.tasks.cleanup_tasks.*': {'queue': 'maintenance'}
}

# Using string names for beat schedule to avoid importing celery.schedules at module import time
CELERYBEAT_SCHEDULE = {
    'daily-publication-indexing': {
        'task': 'app.worker.tasks.indexing_tasks.daily_publication_indexing',
        'schedule': 'crontab(2,0)',
        'options': {'queue': 'indexing'}
    }
}
