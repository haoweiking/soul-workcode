#!/usr/bin/python
# encoding:utf-8

from fabric.api import *
from fabric.colors import *
from fabric.context_managers import *


def staging():
    env.hosts = ['root@staging.yiyun.com']
    env.REMOTE_CODEBASE_PATH = '/srv/apps/yiyun'
    env.servername = 'staging'


def production():
    env.hosts = ['root@web.yiyun.com']
    env.REMOTE_CODEBASE_PATH = '/data1/web/yiyun'
    env.servername = 'production'


def install_requires():
    run("sudo apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev \
        libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk \
        python-chardet")


def gitpull():
    with cd(env.REMOTE_CODEBASE_PATH):
        run('git pull')


def setup_db():
    with cd(env.REMOTE_CODEBASE_PATH):
        run('python manager.py --cmd=createall')


def restart():
    for i in range(1, 5):
        run('supervisorctl -c /etc/supervisor/supervisord.conf restart yiyun:yiyun_900%s' %
            i)


def restart_celery():
    run('supervisorctl -c /etc/supervisor/supervisord.conf restart celery_worker')


def deploy():
    gitpull()
    setup_db()
    restart()
    restart_celery()
