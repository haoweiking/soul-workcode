#!/usr/bin/env python

import re
import json

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.locale
from concurrent.futures import ThreadPoolExecutor

import httpagentparser
from yiyun.ext.forms import TornadoInputWrapper
from yiyun.ext.mixins import PermissionMixin, FlashMessageMixin, SentryMixin
from yiyun.helpers import JSONEncoder, decimalval
from yiyun.libs.tornado_jinja2 import Jinja2Loader

MAX_WORKERS = 10


class BaseHandler(tornado.web.RequestHandler, PermissionMixin, SentryMixin):

    executor = ThreadPoolExecutor(MAX_WORKERS)

    def initialize(self, *args, **kwargs):
        """
            TODO: load settings for host
        """

        self.remote_ip = self.request.headers.get(
            'X-Forwarded-For', self.request.headers.get('X-Real-Ip', self.request.remote_ip))

        proto = self.request.headers.get(
            "X-Scheme", self.request.headers.get("X-Forwarded-Proto", self.request.protocol))
        if proto in ("http", "https"):
            self.request.protocol = proto

    def prepare(self):
        self.db.connect()

    def create_template_loader(self, template_path):
        """使用Jinja2模板引擎"""

        settings = self.application.settings

        kwargs = {}
        if "autoescape" in settings:
            # autoescape=None means "no escaping", so we have to be sure
            # to only pass this kwarg if the user asked for it.
            kwargs["autoescape"] = settings["autoescape"]
        if "template_whitespace" in settings:
            kwargs["whitespace"] = settings["template_whitespace"]

        if settings.get("debug", False):
            kwargs['auto_reload'] = True

        return Jinja2Loader(template_path, **kwargs)

    def on_finish(self):
        try:
            if self.db and not self.db.is_closed():
                self.db.close()
        except:
            pass

    def get_current_user(self):
        # user = self.session['user'] if 'user' in self.session else None
        # return user
        pass

    def get_user_locale(self):
        code = "zh_CN"
        return tornado.locale.get(code)

    def _(self, message, plural_message=None, count=None):
        return message
        # return self.locale.translate(message, plural_message, count)

    @property
    def db(self):
        return self.application.db

    @property
    def redis(self):
        return self.application.redis

    @property
    def logger(self):
        return self.application.logger

    @property
    def current_ua(self):
        return httpagentparser.simple_detect(self.request.headers.get("User-Agent", ""))

    def is_iphone(self):
        return self.request.headers.get("User-Agent", "").lower().find("iphone") > 0

    def is_android(self):
        return self.request.headers.get("User-Agent", "").lower().find("android") > 0

    def is_weixin(self):
        """ 是否在微信里访问
        """
        return self.request.headers.get("User-Agent", "").lower().find("micromessenger") > 0

    def json_encode(self, value):
        return json.dumps(value, cls=JSONEncoder).replace("</", "<\\/")

    def render_string(self, template_name, **kwargs):
        kwargs['json_encode'] = self.json_encode
        kwargs['decimalval'] = decimalval
        kwargs['debug'] = self.settings['debug']
        return super(BaseHandler, self).render_string(template_name, **kwargs)

    def get_args(self, key, default=None, type=None):
        if type == list:
            return self.get_arguments(key)
        value = self.get_argument(key, default)
        if value and type:
            try:
                value = type(value)
            except ValueError:
                value = default
        return value

    @property
    def arguments(self):
        if not hasattr(self, '_arguments'):
            arguments = self.request.arguments
            if self.request.files:
                arguments.update(self.request.files)
            self._arguments = TornadoInputWrapper(arguments)

        return self._arguments

    @property
    def validated_arguments(self):
        """
        获取以校验的请求参数
        Returns:

        """
        assert hasattr(self, '_validated_arguments'), \
            'request.arguments 未校验, 先使用校验装饰器'
        return self._validated_arguments

    @property
    def is_xhr(self):
        '''True if the request was triggered via a JavaScript XMLHttpRequest.
        This only works with libraries that support the `X-Requested-With`
        header and set it to "XMLHttpRequest".  Libraries that do that are
        prototype, jQuery and Mochikit and probably some more.'''
        return self.request.headers.get('X-Requested-With', '') \
                           .lower() == 'xmlhttprequest'

    @property
    def next_url(self):
        return self.get_argument("next", None)

    def flash(self, message, category='info'):
        messages = self.flash_messages()
        messages.append((category, message))
        self.set_secure_cookie(
            'flash_messages', tornado.escape.json_encode(messages), expires_days=None)

    def flash_messages(self):
        messages = self.get_secure_cookie('flash_messages')
        messages = tornado.escape.json_decode(messages) if messages else []
        return messages

    def get_flashed_messages(self):
        messages = self.flash_messages()
        self.clear_cookie('flash_messages')
        return messages

    def write(self, chunk):
        if isinstance(chunk, dict):
            if self.settings['debug']:
                chunk = json.dumps(chunk,
                                   ensure_ascii=False,
                                   sort_keys=True,
                                   cls=JSONEncoder
                                   ).replace("</", "<\\/")
            else:
                chunk = self.json_encode(chunk)

            self.set_header("Content-Type", "application/json; charset=UTF-8")

        super(BaseHandler, self).write(chunk)

    def write_error(self, status_code, **kwargs):
        super(BaseHandler, self).write_error(status_code, **kwargs)

    def write_success(self, **kwargs):
        kwargs['status'] = "ok"
        self.write(kwargs)


class ErrorHandler(BaseHandler):

    """raise 404 error if url is not found.
    fixed tornado.web.RequestHandler HTTPError bug.
    """

    def prepare(self):
        self.set_status(404)
        if self.is_xhr or self.request.headers.get("Accept", "").lower().find("json") > 0:
            self.finish({
                "error": "Not found",
                "error_code": 404
            })
        else:
            raise tornado.web.HTTPError(404)


class StaticFileHandler(tornado.web.StaticFileHandler):

    def get(self, path, include_body=True):

        if path.find("?") > 0:
            path = path.split("?", 2)[0]

        if re.match(r"\-\/.+\.[0-9a-z]{8}\.([0-9a-zA-Z]{2,6})$", path):
            path = re.sub(r"\-\/(.+)\.[0-9a-z]{8}\.([0-9a-zA-Z]{2,6})$", "\g<1>.\g<2>", path)

        elif path.startswith("-/"):
            path = re.sub(r"^\-\/", "", path)

        return super(StaticFileHandler, self).get(path, include_body=include_body)

    @classmethod
    def make_static_url(cls, settings, path, include_version=True):

        prefix = settings.get('static_url_prefix', '/static/')

        url = prefix + path
        if not include_version:
            return url

        version_hash = cls.get_version(settings, path)
        if not version_hash:
            return url

        url = prefix + "-/" + path

        return re.sub(r'\.([0-9a-zA-Z]{2,6})$', ".%s.\g<1>" % version_hash[:8], url)
