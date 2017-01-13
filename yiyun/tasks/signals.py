# coding: utf-8

from celery import current_app as app
from celery.signals import (task_prerun, task_postrun, task_success, task_failure,
                            worker_process_init, worker_process_shutdown,
                            worker_init, worker_ready)

from celery.schedules import crontab


# 定时任务
app.conf.update(
    CELERYBEAT_SCHEDULE = {
        'auto-finish-activity': {
            'task': 'yiyun.tasks.activity.finish_activities',
            'schedule': crontab(minute='*/15')
        },
    }
)

@task_prerun.connect
def task_prerun_handler(sender=None, body=None, **kwargs):
    app.db.connect()


@task_postrun.connect
def task_postrun_handler(sender=None, body=None, **kwargs):
    try:
        app.db.close()
    except:
        pass


@task_success.connect
def task_success_handler(sender=None, body=None, **kwargs):
    pass


@task_failure.connect
def task_failure_handler(sender=None, body=None, **kwargs):
    pass


@worker_init.connect
def worker_init_handler(sender=None, body=None, **kwargs):
    pass


@worker_ready.connect
def worker_ready_handler(sender=None, body=None, **kwargs):
    pass


@worker_process_init.connect
def worker_process_init_handler(sender=None, body=None, **kwargs):
    pass


@worker_process_shutdown.connect
def worker_process_shutdown_handler(sender=None, body=None, **kwargs):
    pass
