#!/usr/bin/env python

import functools
import re

from tornado.auth import (AuthError, OAuth2Mixin, _auth_return_future,
                          escape, httpclient, urllib_parse)

from tornado.httputil import url_concat


class WeiboMixin(OAuth2Mixin):

    """Weibo authentication using OAuth2."""

    _OAUTH_ACCESS_TOKEN_URL = "https://api.weibo.com/oauth2/access_token?"
    _OAUTH_AUTHORIZE_URL = "https://api.weibo.com/oauth2/authorize?"
    _OAUTH_NO_CALLBACKS = False

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                               code, callback, extra_fields=None):
        """Handles the login for the Weibo user, returning a user object.

        Example usage::

            class WeiboLoginHandler(LoginHandler, WeiboMixin):
              @tornado.web.asynchronous
              @tornado.gen.coroutine
              def get(self):
                  if self.get_argument("code", False):
                      user = yield self.get_authenticated_user(
                          redirect_uri="/auth/weibo/",
                          client_id=self.settings["weibo_app_key"],
                          client_secret=self.settings["weibo_app_secret"],
                          code=self.get_argument("code"))
                      # Save the user with e.g. set_secure_cookie
                  else:
                      self.authorize_redirect(
                          redirect_uri="/auth/weibo/",
                          client_id=self.settings["weibo_app_key"],
                          extra_params={"response_type": "code"})
        """
        http = self.get_auth_http_client()
        args = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "extra_params": {
                "grant_type": "authorization_code",
            },
        }

        fields = set(["id", "screen_name", "gender",
                      "profile_image_url", "avatar_hd", "avatar_large", "domain"])
        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._oauth_request_token_url(**args),
                   functools.partial(self._on_access_token, redirect_uri, client_id,
                                     client_secret, callback, fields),
                   method="POST", body="")

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         future, fields, response):
        if response.error:
            future.set_exception(
                AuthError('Weibo auth error: %s' % str(response)))
            return

        args = escape.json_decode(escape.native_str(response.body))
        session = {
            "access_token": args.get("access_token"),
            "expires_in": args.get("expires_in")
        }

        self.weibo_request(
            path="/users/show.json",
            callback=functools.partial(
                self._on_get_user_info, future, session, fields),
            access_token=session["access_token"],
            uid=args.get("uid"))

    def _on_get_user_info(self, future, session, fields, user):
        if user is None:
            future.set_result(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({"access_token": session["access_token"],
                         "session_expires": session.get("expires_in")})
        future.set_result(fieldmap)

    @_auth_return_future
    def weibo_request(self, path, callback, access_token=None,
                      post_args=None, **args):
        """Fetches the given relative API path, e.g., "/users/show.json"

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        An introduction to the Weibo API can be found at
        http://open.weibo.com/wiki/%E5%BE%AE%E5%8D%9AAPI

        Many methods require an OAuth access token which you can
        obtain through `~OAuth2Mixin.authorize_redirect` and
        `get_authenticated_user`. The user returned through that
        process includes an ``access_token`` attribute that can be
        used to make authenticated requests via this method.

        Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              WeiboMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                @tornado.gen.coroutine
                def get(self):
                    new_entry = yield self.weibo_request(
                        "/statuses/update.json",
                        post_args={"status": "I am posting from my Tornado application!"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        self.authorize_redirect()
                        return
                    self.finish("Posted a message!")
        """
        url = "https://api.weibo.com/2" + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(args)

        if all_args:
            url += "?" + urllib_parse.urlencode(all_args)
        callback = functools.partial(self._on_weibo_request, callback)
        http = self.get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST",
                       body=urllib_parse.urlencode(post_args), callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_weibo_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("新浪微博认证失败，请重试"))
            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class QQMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = 'https://graph.qq.com/oauth2.0/token?'
    _OAUTH_AUTHORIZE_URL = 'https://graph.qq.com/oauth2.0/authorize?'

    def authorize_redirect(self, redirect_uri=None, client_id=None,
                           response_type='code', state='authorize', extra_params=None):
        args = {
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'response_type': response_type,
            'state': state,
        }

        if extra_params:
            args.update(extra_params)

        self.redirect(url_concat(self._OAUTH_AUTHORIZE_URL, args))

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret, code,
                               callback, grant_type='authorization_code', extra_fields=None):
        http = self.get_auth_http_client()
        args = {
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': grant_type,
        }

        fields = set(['nickname', 'gender', 'figureurl',
                      'refresh_token', 'figureurl_qq_1', 'figureurl_qq_2'])

        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._oauth_request_token_url(**args),
                   functools.partial(self._on_access_token, redirect_uri, client_id,
                                     client_secret, callback, fields))

    def _oauth_request_token_url(self, redirect_uri=None, client_id=None,
                                 client_secret=None, code=None,
                                 grant_type=None, extra_params=None):

        url = self._OAUTH_ACCESS_TOKEN_URL
        args = {
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': grant_type,
        }

        if extra_params:
            args.update(extra_params)

        return url_concat(url, args)

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         callback, fields, response, future):
        if response.error:
            future.set_exception(AuthError('QQ auth error %s' % str(response)))
            return

        args = escape.parse_qs_bytes(escape.native_str(response.body))
        if args.get("error", None):
            future.set_exception(AuthError('QQ auth error %s' % str(response)))
            return

        session = {
            "access_token": args["access_token"][-1],
            "expires": args.get("expires_in")[0]
        }

        http = self.get_auth_http_client()
        http.fetch(url_concat('https://graph.qq.com/oauth2.0/me?', {'access_token': session['access_token']}),
                   functools.partial(self._on_access_openid, redirect_uri, client_id,
                                     client_secret, session, callback, fields))

    def _on_access_openid(self, redirect_uri, client_id, client_secret, session,
                          future, fields, response):
        if response.error:
            future.set_exception(AuthError('Error response % fetching %s',
                                           response.error, response.request.url))
            return

        res = re.search(
            r'"openid":"([a-zA-Z0-9]+)"', escape.native_str(response.body))

        session['openid'] = res.group(1)
        session['client_id'] = client_id

        self.qq_request(
            path='/user/get_user_info',
            callback=functools.partial(
                self._on_get_user_info, future, session, fields),
            access_token=session['access_token'],
            openid=session['openid'],
            client_id=session['client_id'],
        )

    def _on_get_user_info(self, future, session, fields, user):
        if user is None:
            future.set_result(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({'access_token': session['access_token'], 'session_expires': session.get('expires'),
                         'openid': session['openid']})

        future.set_result(fieldmap)

    @_auth_return_future
    def qq_request(self, path, callback, access_token=None, openid=None, client_id=None,
                   format='json', post_args=None, **args):
        url = 'https://graph.qq.com' + path
        all_args = {}
        if access_token:
            all_args['access_token'] = access_token
        if openid:
            all_args['openid'] = openid
        if client_id:
            all_args['oauth_consumer_key'] = client_id
        if args:
            all_args.update(args)

        if all_args:
            all_args.update({'format': format})
            url += '?' + urllib_parse.urlencode(all_args)
        callback = functools.partial(self._on_qq_request, callback)
        http = self.get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_qq_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("QQ认证失败，请重新"))
            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        return httpclient.AsyncHTTPClient()


class WeixinMixin(OAuth2Mixin):

    """docstring for WeixinMixin"""

    _OAUTH_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/sns/oauth2/access_token?'

    @_auth_return_future
    def get_authenticated_user(self, client_id, client_secret, code, callback, grant_type='authorization_code'):

        http = self.get_auth_http_client()
        args = {
            'code': code,
            'appid': client_id,
            'secret': client_secret,
            'grant_type': grant_type
        }

        url = url_concat(self._OAUTH_ACCESS_TOKEN_URL, args)

        http.fetch(url, functools.partial(self._on_access_token, client_id,
                                          client_secret, callback))

    def _on_access_token(self, client_id, client_secret, future, response):

        if response.error:
            future.set_exception(
                AuthError('Weixin auth error: %s' % str(response)))
            return

        session = escape.json_decode(response.body)

        if session.get("errcode", None):
            future.set_exception(
                AuthError('Weixin auth error: %s' % str(session['errcode'])))
            return

        self.weixin_request('/userinfo',
                            callback=functools.partial(
                                self._on_get_user_info, future, session),
                            access_token=session['access_token'],
                            openid=session['openid']
                            )

    def _on_get_user_info(self, future, session, user):

        if user is None or user.get("errcode", None):
            future.set_exception(
                AuthError('Weixin getuserinfo error: %s' % str(user['errcode'])))
            return

        user.update(session)
        future.set_result(user)

    @_auth_return_future
    def weixin_request(self, path, callback, access_token=None, openid=None, post_args=None, **args):

        url = 'https://api.weixin.qq.com/sns' + path

        all_args = {}
        if access_token:
            all_args['access_token'] = access_token

        if openid:
            all_args['openid'] = openid

        if args:
            all_args.update(args)

        if all_args:
            url += '?' + urllib_parse.urlencode(all_args)

        callback = functools.partial(self._on_weixin_request, callback)
        http = self.get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_weixin_request(self, future, response):
        if response.error:
            future.set_exception(AuthError('Error response %s fetching %s',
                                           response.error, response.request.url))
            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        return httpclient.AsyncHTTPClient()


class DoubanMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = 'https://www.douban.com/service/auth2/token'
    _OAUTH_AUTHORIZE_URL = 'https://www.douban.com/service/auth2/auth?'

    def authorize_redirect(self, redirect_uri=None, client_id=None,
                           response_type='code', extra_params=None):
        args = {
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'response_type': response_type,
        }

        if extra_params:
            args.update(extra_params)

        self.redirect(url_concat(self._OAUTH_AUTHORIZE_URL, args))

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret, code,
                               callback, grant_type='authorization_code', extra_fields=None):
        http = self.get_auth_http_client()
        args = {
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': grant_type,
        }

        fields = set(['id', 'name', 'avatar'])

        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._OAUTH_ACCESS_TOKEN_URL, method="POST",
                   body=urllib_parse.urlencode(args),
                   callback=functools.partial(self._on_access_token, redirect_uri,
                                              client_id, client_secret, callback, fields))

    def _oauth_requeset_token_url(self, rediret_uri=None, client_id=None,
                                  client_secret=None, code=None,
                                  grant_type=None, extra_params=None):
        pass

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         future, fields, response):
        if response.error:
            future.set_exception(
                AuthError('Douban auth error %s' % str(response)))
            return

        args = escape.json_decode(escape.native_str(response.body))
        session = {
            'access_token': args['access_token'],
            'expires': args['expires_in'],
            'refresh_token': args['refresh_token'],
            'douban_user_id': args['douban_user_id'],
        }

        self.douban_request(
            path='/user/~me',
            callback=functools.partial(
                self._on_get_user_info, future, session, fields),
            access_token=session['access_token'],
        )

    def _on_get_user_info(self, future, session, fields, user):
        if user is None:
            future.set_result(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({'access_token': session['access_token'], 'session_expires': session['expires'],
                         'douban_user_id': session['douban_user_id']})

        future.set_result(fieldmap)

    @_auth_return_future
    def douban_request(self, path, callback, access_token=None, post_args=None, **args):
        url = "https://api.douban.com/v2" + path
        all_args = {}
        if args:
            all_args.update(args)

        callback = functools.partial(self._on_douban_request, callback)
        http = self.get_auth_http_client()

        if post_args is not None:
            request = httpclient.HTTPRequest(url, method='POST', headers={
                                             'Authorization': 'Bearer %s' % access_token},
                                             body=urllib_parse.urlencode(post_args))
        elif all_args:
            url += '?' + urllib_parse.urlencode(all_args)
            request = httpclient.HTTPRequest(
                url, headers={'Authorization': 'Bearer %s' % access_token})
        else:
            request = httpclient.HTTPRequest(
                url, headers={'Authorization': 'Bearer %s' % access_token})

        http.fetch(request, callback=callback)

    def _on_douban_request(self, future, response):
        if response.error:
            future.set_exception(AuthError('Error response % fetching %s',
                                           response.error, response.request.url))

            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        return httpclient.AsyncHTTPClient()
