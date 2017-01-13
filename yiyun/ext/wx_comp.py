#!/usr/bin/env python


import requests
import json

from tornado.auth import (AuthError, _auth_return_future,
                          escape, httpclient, urllib_parse)

from tornado.httputil import url_concat

from yiyun.libs.wechat_sdk import WechatBasic
from yiyun.libs.wechat_sdk.exceptions import WechatAPIException
from yiyun.core import current_app as app
from yiyun.ext.cache import cached_property


class WxCompMixin(object):
    """微信公众号第三方平台接口"""

    _WX_COMP_BASE_URL = 'https://api.weixin.qq.com/cgi-bin/component'
    _WX_COMP_LOGIN_URL = 'https://mp.weixin.qq.com/cgi-bin/componentloginpage'

    @cached_property
    def wechat(self):
        self._wechat_client = WechatBasic(
            token=self.settings['wx_comp_token'],
            appid=self.settings['wx_comp_appid'],
            appsecret=self.settings['wx_comp_appsecret'],
            encrypt_mode="safe",
            encoding_aes_key=self.settings['wx_comp_aes_key']
        )

        return self._wechat_client

    def check_signature(self, signature, timestamp, nonce):
        return self.wechat.check_signature(signature, timestamp, nonce)

    def authorize_redirect(self, redirect_uri):
        pre_auth_code = self.create_preauthcode()
        args = {
            'redirect_uri': redirect_uri,
            'component_appid': self.settings['wx_comp_appid'],
            'pre_auth_code': pre_auth_code,
        }

        self.redirect(url_concat(self._WX_COMP_LOGIN_URL, args))

    def parse_message(self, data, msg_signature=None,
                      timestamp=None, nonce=None):
        self.wechat.parse_data(data,
                               msg_signature=msg_signature,
                               timestamp=timestamp,
                               nonce=nonce)

        return self.wechat.get_message()

    def get_message(self):
        return self.wechat.get_message()

    def set_component_verify_ticket(self, ticket, expires=1200):
        self.redis.set("wx:component_verify_ticket", ticket)
        self.redis.expire("wx:component_verify_ticket", expires)

    def get_component_verify_ticket(self):
        return self.redis.get("wx:component_verify_ticket")

    def set_component_access_token(self, component_access_token, expires=6600):
        self.redis.set("wx:component_access_token", component_access_token)
        self.redis.expire("wx:component_access_token", expires)

    def get_component_access_token(self):
        """获取第三方平台component_access_token"""

        access_token = self.redis.get("wx:component_access_token")
        if access_token is None:
            payload = {
                "component_appid": self.settings['wx_comp_appid'],
                "component_appsecret": self.settings['wx_comp_appsecret'],
                "component_verify_ticket": self.get_component_verify_ticket()
            }
            r = requests.post(self._WX_COMP_BASE_URL + "/api_component_token",
                              data=json.dumps(payload),
                              headers={
                                  "Content-Type": "application/json",
                                  "Accept": "application/json"
                              })

            data = r.json()
            if data.get("errcode", None):
                raise WechatAPIException(data['errcode'], data['errmsg'])

            access_token = data['component_access_token']
            self.set_component_access_token(access_token,
                                            data['expires_in'] - 1000)

        return access_token

    def create_preauthcode(self):
        """获取预授权码pre_auth_code"""

        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid']
        }

        r = requests.post(self._WX_COMP_BASE_URL + "/api_create_preauthcode",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data['pre_auth_code']

    def get_query_auth(self, authorization_code):
        """使用授权码换取公众号的接口调用凭据和授权信息"""

        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid'],
            "authorization_code": authorization_code
        }
        r = requests.post(self._WX_COMP_BASE_URL + "/api_query_auth",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data['authorization_info']

    def refresh_authorizer_token(self, authorizer_appid,
                                 authorizer_refresh_token):
        """获取（刷新）授权公众号的接口调用凭据（令牌）"""

        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid'],
            "authorizer_appid": authorizer_appid,
            "authorizer_refresh_token": authorizer_refresh_token
        }
        r = requests.post(self._WX_COMP_BASE_URL + "/api_authorizer_token",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data

    def get_authorizer_info(self, authorizer_appid):
        """获取授权方的公众号帐号基本信息"""

        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid'],
            "authorizer_appid": authorizer_appid,
        }
        r = requests.post(self._WX_COMP_BASE_URL + "/api_get_authorizer_info",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data

    def get_authorizer_option(self, authorizer_appid, option_name):
        """获取授权方的选项设置信息"""

        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid'],
            "authorizer_appid": authorizer_appid,
            "option_name": option_name
        }
        r = requests.post(self._WX_COMP_BASE_URL + "/api_get_authorizer_info",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data

    def set_authorizer_option(self, authorizer_appid, option_name,
                              option_value):
        component_access_token = self.get_component_access_token()
        payload = {
            "component_appid": self.settings['wx_comp_appid'],
            "authorizer_appid": authorizer_appid,
            "option_name": option_name,
            "option_value": option_value
        }
        r = requests.post(self._WX_COMP_BASE_URL + "/api_set_authorizer_option",
                          params={
                              "component_access_token": component_access_token
                          },
                          data=json.dumps(payload),
                          headers={
                              "Content-Type": "application/json",
                              "Accept": "application/json"
                          })
        data = r.json()
        if data.get("errcode", None):
            raise WechatAPIException(data['errcode'], data['errmsg'])

        return data

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()
