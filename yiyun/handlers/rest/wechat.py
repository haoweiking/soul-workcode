import logging
import json
import datetime
import hashlib

from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from yiyun.libs.wxpay import generate_nonce_str
from .base import ApiBaseHandler, rest_app, ApiException


@rest_app.route(r'/wechat/config_signature')
class WechatJSAPITickHandler(ApiBaseHandler):
    REDIS_KEY = {
        'access_token': 'wechat:access_token',
        'ticket': 'wechat:jsapi_ticket'
    }

    @property
    def http_client(self):
        if not hasattr(self, '_http_client'):
            self._http_client = AsyncHTTPClient()
        return self._http_client

    @gen.coroutine
    def post(self):
        ticket = yield self.get_ticket()

        _params = {
            'noncestr': generate_nonce_str(),
            'timestamp': int(datetime.datetime.now().timestamp()),
            'url': self.get_argument('url'),
            'jsapi_ticket': ticket
        }

        pre_args = []
        for k, v in sorted(_params.items()):
            pre_args.append(k + '=' + str(v))

        params_to_str = '&'.join(pre_args)
        logging.debug(params_to_str)
        sign = hashlib.sha1(params_to_str.encode()).hexdigest()

        _params.pop('jsapi_ticket')
        _params['signature'] = sign
        _params['appId'] = self.settings['weixin_appid']

        self.write(_params)

    async def get_ticket(self):
        """
        获取 jsapi ticket, 如果 redis 没有从微信服务器获取
        Returns:

        """
        ticket = self.redis.get(self.REDIS_KEY['ticket'])
        if not ticket:
            logging.debug('redis 没有 ticket, 从微信服务器获取')
            ticket = await self.get_jsapi_ticket()
        logging.debug('ticket: {0}'.format(ticket))
        return ticket

    async def get_jsapi_ticket(self):
        url = ("https://api.weixin.qq.com/cgi-bin/ticket/getticket?"
               "access_token={access_token}&type=jsapi")
        token = self.redis.get(self.REDIS_KEY['access_token'])
        if not token:
            logging.debug('redis 中没有 token, 从微信服务器获取')
            token = await self.obtain_access_token()
        logging.debug('token: {0}'.format(token))

        response = await self.http_client.fetch(url.format(access_token=token))
        result = json.loads(response.body.decode())
        ticket = result.get('ticket')
        if ticket:
            self.redis.set(self.REDIS_KEY['ticket'], ticket)
            self.redis.expire(self.REDIS_KEY['ticket'], 7000)
            return ticket
        else:
            logging.debug('获取 jsapi 出错了: {0}'.format(result))
            raise ApiException(500, result)

    async def obtain_access_token(self):
        """
        从微信服务器获取 access_token
        Returns:

        """
        url = ("https://api.weixin.qq.com/cgi-bin/token?"
               "grant_type=client_credential&"
               "appid={appid}&"
               "secret={appsecret}"
               .format(appid=self.settings['weixin_appid'],
                       appsecret=self.settings['weixin_appsecret']))
        response = await self.http_client.fetch(url)
        result = json.loads(response.body.decode())
        access_token = result.get('access_token')
        if access_token:
            self.redis.set(self.REDIS_KEY['access_token'], access_token)
            self.redis.expire(self.REDIS_KEY['access_token'], 7000)
            return access_token
        else:
            logging.debug('获取 access_token 出错了: {0}'.format(result))
            raise ApiException(500, result)
