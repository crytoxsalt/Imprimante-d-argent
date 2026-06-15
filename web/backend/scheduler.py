"""
Celery Beat scheduler that reads active schedules from the DB and fires jobs.
Run with: celery -A web.backend.tasks.celery_app.celery beat --loglevel=info
"""
from celery.schedules import crontab
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Schedule

_engine = create_engine(settings.database_url_sync)
_Session = sessionmaker(bind=_engine)

PIPELINE_TASKS = {
    "reddit": "web.backend.tasks.generate.reddit",
    "brat": "web.backend.tasks.generate.brat",
    "montage": "web.backend.tasks.generate.montage",
    "stocks_dca": "web.backend.tasks.generate.stocks_dca",
    "stocks_compare": "web.backend.tasks.generate.stocks_compare",
    "familyguy": "web.backend.tasks.generate.familyguy",
    "movies": "web.backend.tasks.generate.movies",
}


def load_schedules_into_beat(celery_app):
    """Called at beat startup to register all active DB schedules."""
    with _Session() as session:
        schedules = session.execute(
            select(Schedule).where(Schedule.is_active == True)
        ).scalars().all()

    beat_schedule = {}
    for s in schedules:
        task_name = PIPELINE_TASKS.get(s.pipeline)
        if not task_name:
            continue
        parts = s.cron_expr.split()
        if len(parts) != 5:
            continue
        minute, hour, dom, month, dow = parts
        beat_schedule[f"schedule-{s.id}"] = {
            "task": task_name,
            "schedule": crontab(minute=minute, hour=hour, day_of_month=dom,
                                month_of_year=month, day_of_week=dow),
            "args": [f"scheduled-{s.id}", s.params],
        }

    celery_app.conf.beat_schedule = beat_schedule
