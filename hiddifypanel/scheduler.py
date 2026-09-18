from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

_scheduler: BackgroundScheduler | None = None


def init_app(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from hiddifypanel.panel import usage
    from hiddifypanel.panel.cli import backup_task
    from hiddifypanel.panel.usage import locked_execute

    def run_in_app_context(func, *args, **kwargs):
        with app.app_context():
            return func(*args, **kwargs)

    scheduler = BackgroundScheduler(job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 30})

    scheduler.add_job(
        run_in_app_context,
        args=(usage.update_local_usage,),
        trigger=IntervalTrigger(seconds=60),
        id="update_usage",
        name="update usage",
    )
    # backup_task has no lock of its own (unlike update_local_usage); wrap it the
    # same way so a future move to multiple granian workers can't run it twice.
    scheduler.add_job(
        run_in_app_context,
        args=(locked_execute, "lock-backup-task", backup_task),
        trigger=CronTrigger(hour="*/6", minute="0"),
        id="backup_task",
        name="backup_task",
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler started: jobs={}", [j.id for j in scheduler.get_jobs()])
    return scheduler
