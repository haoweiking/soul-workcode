# coding: utf-8

import hashlib
import os
import time
from urllib import parse

import requests
from celery import current_app as app
from tornado import template

from yiyun.core import celery
from yiyun.models import User
from yiyun.tasks import qiniu_tool
from yiyun.tasks.message import send_email


@celery.task
def send_verify_email(name, email, verify_code, verify_url):

    tpl_dir = os.path.join(app.settings.get("template_path", ""), "email")
    loader = template.Loader(tpl_dir)

    html = loader.load("verify_email.html").generate(
        name=name, verify_code=verify_code,
        email=email, verify_url=verify_url)

    send_email(email, "请验证你的电子邮箱地址", html)


@celery.task
def send_forgot_email(name, email, verify_code, verify_url):

    tpl_dir = os.path.join(app.settings.get("template_path", ""), "email")
    loader = template.Loader(tpl_dir)

    query_args = parse.urlencode({"email": email, "code": verify_code})

    html = loader.load("forgot_password.html").generate(
        name=name, email=email, verify_url=verify_url,
        query_args=query_args)

    send_email(email, "找回密码", html)


@celery.task
def update_avatar_by_url(user_id, avatar_url):

    r = requests.get(avatar_url)

    if r.status_code != 200:
        return

    avatar_key = "user:%s%s" % (user_id, time.time())
    avatar_key = hashlib.md5(avatar_key).hexdigest()

    avatar_bucket = app.settings['qiniu_avatar_bucket']

    ret, info = qiniu_tool.put_data(avatar_bucket, avatar_key, r.content,
                                    mime_type="image/jpeg",
                                    check_crc=True
                                    )
    if not ret:
        raise Exception("上传头像失败")

    # 记录保存仓库和位置
    avatar_key = "qiniu:%s:%s" % (avatar_bucket, avatar_key)

    User.update(
        avatar_key=avatar_key
    ).where(
        User.id == user_id
    ).execute()
