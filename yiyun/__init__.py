#!/usr/bin/env python

import logging

import tornado.web
import tornado.wsgi

from raven.contrib.tornado import AsyncSentryClient

from yiyun.helpers import setting_from_object

from yiyun.ext.routing import Route
from yiyun.core import db, redis, celery
from yiyun.core import current_app as app

from yiyun.handlers import ErrorHandler, StaticFileHandler
from yiyun.handlers import admin, web, club, rest

from . import settings as default_settings


def create_app(config=None, use_db_pool=True, ioloop=None):

    settings = setting_from_object(default_settings)

    if isinstance(config, dict):
        settings.update(config)

    handlers = [] + Route.routes()

    # Custom 404 ErrorHandler
    handlers.append((r"/(.*)", ErrorHandler))

    settings['static_handler_class'] = StaticFileHandler
    app.initialize(tornado.web.Application(handlers, **settings))

    if ioloop:
        from .libs.peewee_async import PooledMySQLDatabase
        from .libs.peewee_async import RetryMySQLDatabase
    else:
        from playhouse.pool import PooledMySQLDatabase
        from .ext.database import RetryMySQLDatabase

    # configure database
    if use_db_pool:
        db_conn = PooledMySQLDatabase(app.settings['db_name'],
                                      host=app.settings['db_host'],
                                      user=app.settings['db_user'],
                                      passwd=app.settings['db_passwd'],
                                      port=app.settings['db_port'],
                                      use_unicode=True,
                                      charset="utf8mb4",
                                      threadlocals=False,
                                      max_connections=app.settings[
                                          'db_max_conns'],
                                      stale_timeout=1800
                                      )
    else:
        db_conn = RetryMySQLDatabase(app.settings['db_name'],
                                     host=app.settings['db_host'],
                                     user=app.settings['db_user'],
                                     passwd=app.settings['db_passwd'],
                                     port=app.settings['db_port'],
                                     use_unicode=True,
                                     charset="utf8mb4"
                                     )

    db.initialize(db_conn)
    redis.init_app(app)

    app.db = db_conn
    app.redis = redis

    if ioloop:
        ioloop.run_until_complete(db_conn.connect_async())

    celery.conf.update(BROKER_URL=app.settings['celery_broker_url'],
                       CELERY_RESULT_BACKEND=app.settings['celery_result_url'],
                       CELERY_TASK_SERIALIZER='json',
                       CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
                       CELERY_RESULT_SERIALIZER='json',
                       CELERY_TASK_RESULT_EXPIRES=18000,
                       CELERY_TIMEZONE='Asia/Shanghai',
                       CELERY_ENABLE_UTC=False,
                       CELERYBEAT_SCHEDULE=app.settings["celerybeat_schedule"],
                       )

    celery.settings = app.settings
    celery.db = db
    celery.redis = redis

    logging.basicConfig(level=logging.DEBUG if app.settings['debug'] else logging.WARNING,
                        format='%(asctime)s:%(msecs)03d %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M'
                        )

    app.logger = logging.getLogger(str(app.__class__))
    app.logger.setLevel(
        logging.DEBUG if app.settings['debug'] else logging.WARNING)

    if app.settings['sentry_dsn']:
        app.sentry_client = AsyncSentryClient(app.settings['sentry_dsn'])
        # app = Sentry(app, client=app.raven_client)
    else:
        app.sentry_client = None

    return app
