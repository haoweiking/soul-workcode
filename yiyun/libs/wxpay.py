#! /usr/bin/env python

import logging
import datetime
import random
import string
import hashlib
from collections import OrderedDict
from urllib.parse import urljoin

import xmltodict

from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest
from tornado import gen


def sign_params(params, key):
    """
    对请求参数进行签名
    Args:
        params: 请求参数
        key: 密钥

    Returns: 签名字符串

    """
    pre_args = []
    for k, v in sorted(params.items()):
        pre_args.append(k + '=' + str(v))

    string_from_params = '&'.join(pre_args)
    string_for_sign = string_from_params + '&key=' + key
    logging.debug('String for sign: [{0}]'.format(string_for_sign))
    hashed = hashlib.md5(string_for_sign.encode()).hexdigest().upper()
    return hashed


def generate_nonce_str(length=32):
    """
    生成固定长度的随机字符串, 无符号
    Args:
        length: 长度

    Returns:

    """
    return ''.join(random.sample(string.ascii_letters + string.digits, length))


class WxPay(object):
    """
    微信支付 Mixin
    """

    API_BASE = 'https://api.mch.weixin.qq.com/'

    def __init__(self, appid, mch_id, secret_key, ca_certs=None,
                 client_key=None, client_cert=None):
        """
        Args:
            appid:
            mch_id:
            secret_key:
            ca_certs: 根证书路径
            client_key: 证书密钥的路径
            client_cert: 证书的路径
        """
        self.appid = appid
        self.mch_id = mch_id
        self.secret_key = secret_key
        self.ca_certs = ca_certs
        self.client_key = client_key
        self.client_cert = client_cert

    def get_client(self):
        client = AsyncHTTPClient()
        # client = HTTPClient()
        return client

    @property
    def client(self):
        return self.get_client()

    def build_xml_body(self, params):
        """
        生成 xml
        Args:
            params:

        Returns:

        """
        _params = {}
        _params.update(xml=params)
        xml = xmltodict.unparse(_params)
        return xml

    def _sign_params(self, params, key):
        """
        对请求参数进行签名
        Args:
            params: 请求参数
            key: 密钥

        Returns: 签名字符串

        """
        l = []
        for k, v in sorted(params.items()):
            l.append(k + '=' + v)

        string_from_params = '&'.join(l)
        string_for_sign = string_from_params + '&key=' + key
        logging.debug(string_for_sign)
        hashed = hashlib.md5(string_for_sign.encode()).hexdigest().upper()
        return hashed

    def _prepare_xml_body(self, params):
        """
        构造微信支付 xml
        :param params:
        :return:
        """
        _params = dict(
            appid=self.appid,
            mch_id=self.mch_id,
            nonce_str=generate_nonce_str(),
        )
        _params.update(params)

        sign = sign_params(_params, self.secret_key)
        _params['sign'] = sign
        return self.build_xml_body(_params)

    def get_nonce_str(self):
        return generate_nonce_str()

    def handle_response(self, response):
        if not response.error:
            result = xmltodict.parse(response.body.decode())
            xml = result['xml']
            logging.debug(xml)
            if xml['return_code'] == 'SUCCESS' and\
                    xml['result_code'] == 'SUCCESS':
                return xml
        logging.error('调用微信支付失败: {0}'.format(response.body))
        raise Exception('调用微信支付失败: {0}'.format(response.body))

    @gen.coroutine
    def new_unified_order(self, out_trade_no, body, total_fee,
                          spbill_create_ip, notify_url,
                          openid=None,
                          trade_type='APP'):
        """
        生成新的 微信支付订单

        PATH = 'pay/unifiedorder'
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_1

        Args:
            out_trade_no: 商户系统内部的订单号, 32个字符内、可包含字母,
            body: 商品或支付简要描述
            total_fee: 订单总金额, 单位为分
            spbill_create_ip: APP和网页支付提交用户端ip
            notify_url: 接收微信支付异步通知回调地址,
                        通知url必须为直接可访问的url, 不能携带参数
            openid: trade_type=JSAPI，此参数必传，用户在商户appid下的唯一标识
            trade_type: 交易类型, JSAPI, NATIVE, APP, 默认 APP

        Returns:

        """
        path = 'pay/unifiedorder'
        url = self.API_BASE + path

        nonce_str = ''.join(
            random.sample(string.ascii_letters + string.digits, 32)
        )
        # 将金额转换成分
        total_fee = '{0:.0f}'.format(total_fee * 100)

        params = dict(
            out_trade_no=out_trade_no,
            body=body,
            total_fee=total_fee,
            spbill_create_ip=spbill_create_ip,
            notify_url=notify_url,
            trade_type=trade_type,
            nonce_str=nonce_str
        )
        if trade_type == 'JSAPI' and not openid:
            raise TypeError('trade_type 为 JSAPI 时, openid 必传')
        if trade_type == 'JSAPI' and openid:
            params['openid'] = openid
        xml_body = self._prepare_xml_body(params)
        response = yield self.client.fetch(url, method='POST', body=xml_body)
        return self.handle_response(response)

    @gen.coroutine
    def order_query(self, out_trade_no, transaction_id=None):
        """
        查询订单
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_2

        :param transaction_id: 微信订单号
        :param out_trade_no: 商户系统内部订单号
        :return:
        """
        path = 'pay/orderquery'
        url = self.API_BASE + path

        params = dict(
            out_trade_no=out_trade_no,
        )
        if transaction_id:
            params['transaction_id'] = transaction_id

        xml_body = self._prepare_xml_body(params=params)
        response = yield self.client.fetch(url, method='POST', body=xml_body)
        return self.handle_response(response)

    @gen.coroutine
    def close_order(self, out_trade_no):
        """
        关单接口
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_3

        订单生成后不能马上调用关单接口，最短调用时间间隔为5分钟。
        Args:
            out_trade_no: 商户系统内部订单号
        """
        path = 'pay/closeorder'
        url = self.API_BASE + path

        params = {
            'out_trade_no': out_trade_no
        }
        xml_body = self._prepare_xml_body(params)
        response = yield self.client.fetch(url, method='POST', body=xml_body)
        return self.handle_response(response)

    def refund(self, out_trade_no, out_refund_no, total_fee, refund_fee,
               refund_fee_type='CNY', transaction_id=None, op_user_id=None):
        """
        退款接口
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_4
        Args:
            out_trade_no: 商户测订单
            out_refund_no: 商户系统内部退款单号
            total_fee: 订单总金额, 单位为分
            refund_fee: 退款总金额，订单总金额，单位为分
            refund_fee_type: 货币类型, 默认 CNY
            op_user_id: 操作员帐号, 默认为商户号
            transaction_id: 微信生成的订单
        """
        path = 'secapi/pay/refund'
        url = self.API_BASE + path
        params = dict(
            out_trade_no=out_trade_no,
            out_refund_no=out_refund_no,
            total_fee='{0:.0f}'.format(total_fee * 100),
            refund_fee='{0:.0f}'.format(refund_fee * 100),
            refund_fee_type=refund_fee_type,
        )

        if transaction_id:
            params['transaction_id'] = transaction_id
        params['op_user_id'] = self.mch_id or op_user_id

        xml_body = self._prepare_xml_body(params=params)

        client = HTTPClient()
        request = HTTPRequest(url, method="POST", body=xml_body,
                              ca_certs=self.ca_certs,
                              client_key=self.client_key,
                              client_cert=self.client_cert)
        response = client.fetch(request)

        return self.handle_response(response)

    @gen.coroutine
    def refund_query(self, out_trade_no, transaction_id=None,
                     out_refund_no=None, refund_id=None):
        """
        查询退款
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_5
        Args:
            out_trade_no: 商户系统内部的订单号
            transaction_id: 微信订单号
            out_refund_no: 商户侧传给微信的退款单号
            refund_id: 微信生成的退款单号，在申请退款接口有返回
        """
        path = 'pay/refundquery'
        url = self.API_BASE + path
        if not (out_trade_no or transaction_id or out_refund_no or refund_id):
            raise TypeError('参数 "out_trade_no", "transaction_id", '
                            '"out_refund_no", "refund_id" 四选一')
        params = {
            'transaction_id': transaction_id,
            'out_trade_no': out_trade_no,
            'out_refund_no': out_refund_no,
            'refund_id': refund_id
        }

        xml_body = self._prepare_xml_body(params)
        response = yield self.client.fetch(url, method='POST', body=xml_body)
        return self.handle_response(response)

    @gen.coroutine
    def download_bill(self, bill_date, bill_type='ALL'):
        """
        下载对账单
        https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_6
        Args:
            bill_date: 下载对账单日期
            bill_type: ALL，返回当日所有订单信息，默认值,
                       SUCCESS, 返回当日成功支付的订单
                       REFUND, 返回当日退款订单
        :return:
        """
        path = 'pay/downloadbill'
        url = self.API_BASE + path

        params = dict(
            bill_date=bill_date,
            bill_type=bill_type
        )

        xml_body = self._prepare_xml_body(params)
        response = yield self.client.fetch(url, method='POST', body=xml_body)
        return self.handle_response(response)

    def sign_params(self, params, key):
        """
        对请求参数进行签名
        Args:
            params: 请求参数
            key: 密钥

        Returns: 签名字符串

        """
        pre_args = []
        for k, v in sorted(params.items()):
            pre_args.append(k + '=' + str(v))

        string_from_params = '&'.join(pre_args)
        string_for_sign = string_from_params + '&key=' + key
        logging.debug('String for sign: [{0}]'.format(string_for_sign))
        hashed = hashlib.md5(string_for_sign.encode()).hexdigest().upper()
        return hashed


class WxPayMixin(object):
    DEFAULT_TRADE_TYPE = 'APP'

    @property
    def wxpay(self):
        if not hasattr(self, '_wxpay'):
            self._wxpay = WxPay(appid=self.settings['wxpay_appid'],
                                mch_id=self.settings['wxpay_mchid'],
                                secret_key=self.settings['wxpay_secret_key'])
        return self._wxpay

    @gen.coroutine
    def handle_wxpay(self, pre_order, *args, **kwargs):
        """
        生成微信支付订单
        Args:
            pre_order: 预支付订单
            *args:
            **kwargs:

        Returns:

        """
        consume_info = pre_order.get_info()

        wxpay = self.wxpay

        # TODO: 完成微信支付异步调用
        notify_url = urljoin(self.request.full_url(),
                             self.reverse_url('api_wxpay_callback'))

        trade_type = kwargs.pop('trade_type', self.DEFAULT_TRADE_TYPE)
        params = {
            'trade_type': trade_type
        }
        if trade_type == 'JSAPI':
            params['openid'] = self.current_user.pay_openid
        logging.debug(params)

        prepay = yield wxpay.new_unified_order(
            out_trade_no='%s%s' % (trade_type[0], pre_order.order_no),
            body=kwargs.pop('body', '参加活动'),
            total_fee=pre_order.payment_fee,
            spbill_create_ip=self.request.remote_ip,
            notify_url=notify_url,
            **params
        )

        logging.debug(prepay)
        payment_data = {
            'appId': self.wxpay.appid,
            'timeStamp': int(datetime.datetime.now().timestamp()),
            'nonceStr': self.wxpay.get_nonce_str(),
            'package': "prepay_id={0}".format(prepay['prepay_id']),
            'signType': 'MD5',
        }
        payment_data['paySign'] = self.wxpay.sign_params(
            payment_data,
            self.wxpay.secret_key
        )
        if prepay['trade_type'] == 'NATIVE':
            payment_data['code_url'] = prepay['code_url']
        pre_order.payment_data = payment_data
        pre_order.save()

        consume_info['wxpay'] = payment_data

        return consume_info

    def come_from_wxpay(self, body, key):
        """
        校验通知是否来自微信服务器
        Args:
            body:
            key:

        Returns:

        """


if __name__ == '__main__':
    logging = logging.getLogger('root')
    logging.setLevel('DEBUG')
    wxpay = WxPay(appid='wxd678efh567hg6787', mch_id='1230000109',
                  secret_key='192006250b4c09247ec02edce69f6a2d')
    # wxpay.new_unified_order(out_trade_no='20150806125346', body='商品描述',
    #                         total_fee='100',
    #                         spbill_create_ip='123.12.12.123',
    #                         notify_url='http://example.com/wxpay')
    rst = wxpay.refund(
        out_trade_no="12333333",
        out_refund_no="1233333",
        total_fee=100,
        refund_fee=100
    )

    print(rst)
