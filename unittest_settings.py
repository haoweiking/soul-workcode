# coding=utf-8
import os

BASEDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)))

DEBUG = True

# mysql server config
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
DB_USER = os.environ.get("MYSQL_USER", "root")
DB_PASSWD = os.environ.get("MYSQL_PASSWORD", "pass123")
DB_NAME = os.environ.get("MYSQL_DATABASE", "test_yiyun")

# redis connection config
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_URL = 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT)
CELERY_BROKER_URL = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_URL = 'redis://%s:%s/2' % (REDIS_HOST, REDIS_PORT)
