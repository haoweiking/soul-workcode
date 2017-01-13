"""
修复已添加的`比赛开始推送`任务
"""
from yiyun.models import MatchStartCeleryTask
from yiyun.core import celery


def fix_match_start_notify():
    tasks = MatchStartCeleryTask.select() \
        .where(MatchStartCeleryTask.done.is_null())
    for task in tasks:
        celery.control.revoke(task.task_id, terminate=True)
