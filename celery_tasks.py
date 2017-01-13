#!/usr/bin/env python

from yiyun.core import celery
from yiyun import create_app
from yiyun import tasks

from yiyun.helpers import setting_from_object
import local_settings

if __name__ == "__main__":

    settings = setting_from_object(local_settings)
    app = create_app(settings)

    celery.start()
