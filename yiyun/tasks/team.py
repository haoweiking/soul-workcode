# coding: utf-8

from celery import current_app as app
from yiyun.core import celery

from yiyun.models import Team


@celery.task
def approve_team(team_id):
    Team.update(
        state=1
    ).where(
        (Team.id == team_id
         ) & (Team.state == 0)
    ).execute()
