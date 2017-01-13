# coding: utf-8

import os
import time
import hashlib
import json

import requests
from tornado import template

# from celery import current_app as app
from yiyun.core import celery, current_app as app

from yiyun.models import User

from yiyun.tasks import qiniu_tool
from yiyun.tasks.message import send_email
from yiyun.ext.wx_comp import WxCompMixin


class WxCompClient(WxCompMixin):

    @property
    def redis(self):
        return app.redis

    @property
    def settings(self):
        return app.settings


@celery.task
def reply_tester(auth_code, touser):

    webchat = WxCompClient()
    auth_info = webchat.get_query_auth(auth_code)

    reply = {
        "touser": touser,
        "msgtype": "text",
        "text": {
            "content": "%s_from_api" % auth_code
        }
    }

    requests.post("https://api.weixin.qq.com/cgi-bin/message/custom/send",
                  params={
                      "access_token": auth_info['authorizer_access_token']
                  },
                  json=reply
                  )
