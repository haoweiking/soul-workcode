from functools import wraps

import click

from yiyun.core import celery
from yiyun import create_app
from yiyun import tasks

from yiyun.helpers import setting_from_object
import local_settings


def init(func):

    @wraps(func)
    def init_app(*args, **kwargs):
        settings = setting_from_object(local_settings)
        app = create_app(settings)

        return func(*args, **kwargs)

    return init_app


@click.group()
def cli():
    pass


@cli.command()
@init
def finish_activities():
    """批量结算活动场次"""

    tasks.activity.finish_activities()


if __name__ == '__main__':
    cli()
