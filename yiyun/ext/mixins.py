import functools
import json

import tornado.escape
from hashlib import md5
from tornado.auth import httpclient, urllib_parse, _auth_return_future
from raven.contrib.tornado import SentryMixin as BaseSentryMixin
from yiyun.ext.permission import Identity, AnonymousIdentity


class FlashMessageMixin(object):

    """
        Store a message between requests which the user needs to see.

        views
        -------

        self.flash("Welcome back, %s" % username, 'success')

        base.html
        ------------

        {% set messages = handler.get_flashed_messages() %}
        {% if messages %}
        <div id="flashed">
            {% for category, msg in messages %}
            <span class="flash-{{ category }}">{{ msg }}</span>
            {% end %}
        </div>
        {% end %}
    """

    def flash(self, message, category='message'):
        messages = self.messages()
        messages.append((category, message))
        self.set_secure_cookie(
            'flash_messages', tornado.escape.json_encode(messages))

    def messages(self):
        messages = self.get_secure_cookie('flash_messages')
        messages = tornado.escape.json_decode(messages) if messages else []
        return messages

    def get_flashed_messages(self):
        messages = self.messages()
        self.clear_cookie('flash_messages')
        return messages


class PermissionMixin(object):

    @property
    def identity(self):
        if not hasattr(self, "_identity"):
            self._identity = self.get_identity()
        return self._identity

    def get_identity(self):
        if self.current_user:
            identity = Identity(self.current_user.id)
            identity.provides.update(self.current_user.provides)
            return identity
        return AnonymousIdentity()


class SentryMixin(BaseSentryMixin):

    def get_sentry_user_info(self):

        try:
            user = self.get_current_user()
        except:
            user = None

        return {
            'user': {
                'is_authenticated': True if user else False,
                "current_user_id": user.id if user else False,
            }
        }


class QiniuMixin(object):
    """docstring for QiniuMixin"""

    pass


class AMapError(Exception):
    pass


class AMapMixin(object):
    """docstring for AMapMixin"""

    def get_http_client(self):
        return httpclient.AsyncHTTPClient()

    def params_filter(self, params):
        parts = []
        for k, v in params.items():
            if k not in ('sig', 'sig_type') and v != '':
                parts.append('%s=%s' % (k, v))

        return "&".join(sorted(parts))

    def ampa_sign(self, params):
        params_str = self.params_filter(params)
        return md5((params_str + self.settings["amap_rest_secret"]).encode()).hexdigest()

    @_auth_return_future
    def get_geocode(self, city, address, callback):
        params = {
            "city": city,
            "address": address,
            "key": self.settings['amap_rest_key']
        }

        params['sig'] = self.ampa_sign(params)

        url = "http://restapi.amap.com/v3/geocode/geo?" + \
            urllib_parse.urlencode(params)

        http = self.get_http_client()
        http.fetch(url, callback=functools.partial(self._on_get_geocode, callback))

    def _on_get_geocode(self, future, response):
        if response.error:
            future.set_exception(AMapError("解析地址失败"))
            return

        future.set_result(json.loads(response.body.decode()))
