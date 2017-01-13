#!/usr/bin/env python


import tornado.wsgi
from yiyun import create_app

from yiyun.helpers import setting_from_object
import local_settings

settings = setting_from_object(local_settings)

app = tornado.wsgi.WSGIAdapter(create_app(settings))
