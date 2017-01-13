from peewee import Proxy
from celery import Celery

from yiyun.ext.redis_ext import Redis
from yiyun.ext.proxy import LocalProxy

db = Proxy()
redis = Redis()
celery = Celery("yiyun")
current_app = LocalProxy()
