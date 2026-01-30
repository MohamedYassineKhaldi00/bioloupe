from app.worker.beat_schedule import get_beat_schedule


def test_get_beat_schedule_contains_daily():
    sched = get_beat_schedule()
    assert 'daily-publication-indexing' in sched
    assert sched['daily-publication-indexing']['task'].endswith('daily_publication_indexing')
