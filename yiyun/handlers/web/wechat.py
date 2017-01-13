#!/usr/bin/env python

import functools
import datetime
import logging
import json
from urllib.parse import urlencode, urljoin, unquote

import jwt
from tornado.escape import json_encode
import tornado.web
from tornado.web import HTTPError
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from itsdangerous import SignatureExpired, BadSignature

from .base import WebBaseHandler, web_app
from yiyun.models import TeamOAuthUser, User


class WechatOauth(object):
    OAUTH_URL = ("https://open.weixin.qq.com/connect/oauth2/authorize?"
                 "appid={appid}&"
                 "{redirect_uri}&"
                 "response_type=code&"
                 "scope={scope}&"
                 "state={state}#wechat_redirect")
    COMPONENT_OAUTH_URL = ("https://open.weixin.qq.com/connect/oauth2/"
                           "authorize?"
                           "appid={appid}&"
                           "{redirect_uri}&"
                           "response_type=code&"
                           "scope={scope}&"
                           "state={state}&"
                           "component_appid={component_appid}#wechat_redirect")
    REQUEST_TOKEN_URL = ("https://api.weixin.qq.com/sns/oauth2/access_token?"
                         "appid={appid}&"
                         "secret={secret}&"
                         "code={code}&"
                         "grant_type=authorization_code")
    USER_INFO_URL = ("https://api.weixin.qq.com/sns/userinfo?"
                     "access_token={access_token}&"
                     "openid={openid}&lang=zh_CN")

    def __init__(self, appid, secret):
        self.appid = appid
        self.secret = secret
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncHTTPClient()
        return self._client

    def get_oauth_url(self, appid, redirect_uri, scope='snsapi_userinfo',
                      state=None):
        """
        获取微信 oauth_url
        Args:
            appid: 公众号 APPID
            redirect_uri: 认证后的回调地址, 需要 urlencode
            scope: 授权作用域 默认 snsapi_userinfo
            state:

        Returns:

        """
        url = self.OAUTH_URL.format(appid=appid, redirect_uri=redirect_uri,
                                    scope=scope, state=state)
        return url

    async def get_token(self, code):
        """
        获取 access_token
        Args:
            code: 微信服务器回调返回的 code

        Returns:

        """
        url = self.REQUEST_TOKEN_URL.format(appid=self.appid,
                                            secret=self.secret,
                                            code=code)
        response = await self.client.fetch(url)
        return response


def login(request, user, expires_days=30):
    """
    设置 Cookie 登录
    Args:
        request: tornado.web.Request
        user: User
        expires_days:

    Returns:

    """
    request.set_secure_cookie(name='club_session',
                              value=json_encode({'id': user.id}),
                              expires_days=expires_days)


def wechat_oauth_url(request, state=""):
    """
    获取微信认证的 url
    Args:
        request: tornado.web.RequestHandle

    Returns:

    """
    next_url = request.request.full_url()

    scope = 'snsapi_base'
    appid = request.settings['weixin_appid']
    component_appid = request.settings['wx_comp_appid']

    # Fixme: 回调的地址每个公众号需要是唯一的
    redirect_uri = urljoin(request.request.full_url(),
                           request.reverse_url(name='wechat_oauth'))
    # redirect_uri += '?' + urlencode(dict(next_url=next_url))
    # state = ''
    url = WechatOauth.OAUTH_URL
    # url = WechatOauth.COMPONENT_OAUTH_URL
    url = url.format(appid=appid, scope=scope, state=state,
                     redirect_uri=urlencode({'redirect_uri': redirect_uri}),
                     component_appid=component_appid)
    logging.debug(url)
    return url


@web_app.route(r'/wechat/oauth', name='wechat_oauth')
class WechatOauthHandler(WebBaseHandler):
    """
    微信网页授权获取支付时使用的 openid 回调
    """

    def get_current_user(self):
        access_token = self.get_access_token()
        if access_token:
            try:
                user, data = User.verify_auth_token(access_token)
                if user is None:
                    self.logger.debug("非法会话: %s" % data)
                    raise HTTPError(403, "用户不存在")

                if not user.is_active():
                    raise HTTPError(403, "用户不允许登录")

                return user

            except jwt.ExpiredSignatureError:
                raise HTTPError(403, "会话过期")

            except jwt.InvalidTokenError:
                raise HTTPError(403, "会话无效")

        return None

    def get_access_token(self):
        auth_code = self.request.headers.get("X-Access-Token", None)
        if auth_code:
            return auth_code.strip()

        auth_code = self.get_secure_cookie("access-token")
        if auth_code:
            return auth_code.strip()

        auth_code = self.get_argument("access_token", None)
        if auth_code:
            return auth_code.strip()
            
        auth_code = self.get_argument("state", None)
        if auth_code:
            return auth_code.strip()

    @gen.coroutine
    def get(self):

        if not self.current_user:
            raise HTTPError(403, "未登录")

        next_url = self.get_argument("next_url", "")
        if self.current_user.pay_openid:
            self.set_cookie("pay_openid", self.current_user.pay_openid)
            self.redirect(next_url)
            return

        code = self.get_argument('code', None)
        if code is None:
            self.set_cookie("next_url", next_url)
            self.redirect(wechat_oauth_url(self, self.get_access_token()))
            return

        # state = self.get_argument('state')
        # if not code:
        #     logging.debug('用户没有授权')
        #     raise tornado.web.HTTPError(400)

        # 使用 code 换取 access_token
        url = ("https://api.weixin.qq.com/sns/oauth2/access_token?"
               "appid={appid}&"
               "secret={secret}&"
               "code={code}&"
               "grant_type=authorization_code"
               .format(appid=self.settings['weixin_appid'],
                       secret=self.settings['weixin_appsecret'],
                       code=code,))

        client = AsyncHTTPClient()
        response = yield client.fetch(url)
        if response.code != 200:
            raise HTTPError(500)

        result = json.loads(response.body.decode())
        logging.debug(result)

        user = self.current_user
        user.pay_openid = result['openid']
        user.save()

        self.set_cookie("pay_openid", result['openid'])

        next_url = self.get_cookie("next_url")
        if next_url:
            self.redirect(next_url)
        else:
            self.redirect("/")


@web_app.route(r'/wechat/oauth/callback', name='wechat_oauth_callback')
class WechatOAuthCallbackHandler(WebBaseHandler):
    """
    微信网页授权获取用户信息的回调处理
    """

    @gen.coroutine
    def get(self, *args, **kwargs):
        # Fixme: 使用 wechat_sdk
        # 通过 code 获取 access_token
        code = self.get_argument('code', None)
        state = self.get_argument('state', None)
        url = ("https://api.weixin.qq.com/sns/oauth2/access_token?"
               "appid={appid}&"
               "secret={secret}&"
               "code={code}&"
               "grant_type=authorization_code"
               .format(appid=self.settings['weixin_appid'],
                       secret=self.settings['weixin_appsecret'],
                       code=code,))

        client = AsyncHTTPClient()
        response = yield client.fetch(url)
        if response.code != 200:
            raise HTTPError(500)
        result = json.loads(response.body.decode())

        # Fixme: openid 放在 cookie 中, 不安全, 需要移除
        self.set_secure_cookie(name='yiyun_session', value=result['openid'])

        auth_user, created = TeamOAuthUser\
            .get_or_create(service='weixin', openid=result['openid'])
        if created:
            TeamOAuthUser.update(access_token=result['access_token'],
                                 expires_in=result['expires_in'],
                                 refresh_token=result['refresh_token'])

            info_url = ("https://api.weixin.qq.com/sns/userinfo?"
                        "access_token={access_token}&"
                        "lang=zh_CN"
                        .format(access_token=result['access_token']))
            response = yield client.fetch(info_url)
            if response.code != 200:
                raise HTTPError(500)

            info = json.loads(response.body.decode())
            auth_user.user_info = info
            auth_user.save()

        next_url = self.get_argument('next')

        if auth_user.user is None:
            self.redirect(self.reverse_url(name='mobile_required') +
                          '?next=' + unquote(next_url))
        else:
            login(self, auth_user.user)
            self.redirect(next_url)
