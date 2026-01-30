from __future__ import annotations

try:
    from celery.schedules import crontab
    celery_available = True
except Exception:
    crontab = None
    celery_available = False


def get_beat_schedule():
    if celery_available and crontab is not None:
        return {
            'daily-publication-indexing': {
                'task': 'app.worker.tasks.indexing_tasks.daily_publication_indexing',
                'schedule': crontab(hour=2, minute=0),
                'options': {'queue': 'indexing'}
            },
            'topic-subscriptions': {
                'task': 'app.worker.tasks.indexing_tasks.index_topic_subscriptions',
                'schedule': crontab(hour=3, minute=0),
                'options': {'queue': 'indexing'}
            }
        }
    # Fallback simple dict for tests when celery not installed
    return {
        'daily-publication-indexing': {
            'task': 'app.worker.tasks.indexing_tasks.daily_publication_indexing',
            'schedule': 'crontab(2,0)',
            'options': {'queue': 'indexing'}
        }
    }
