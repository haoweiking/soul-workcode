#!/usr/bin/env python
# encoding:utf-8

import types
from urllib.parse import urlencode
import base64
from hashlib import md5
from urllib.parse import quote_plus

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA


class AlipayMixin(object):

    # 网关地址
    _GATEWAY = 'https://www.alipay.com/cooperate/gateway.do?'
    _REFUND_GATEWAY = 'https://mapi.alipay.com/gateway.do?'

    def smart_str(self, s, encoding='utf-8', strings_only=False, errors='strict'):
        """
        Returns a bytestring version of 's', encoded as specified in 'encoding'.

        If strings_only is True, don't convert (some) non-string-like objects.
        """
        if strings_only and isinstance(s, (type(None), int)):
            return s
        if not isinstance(s, str):
            try:
                return str(s)
            except UnicodeEncodeError:
                if isinstance(s, Exception):
                    # An Exception subclass containing non-ASCII data that doesn't
                    # know how to print itself properly. We shouldn't raise a
                    # further exception.
                    return ' '.join([self.smart_str(arg, encoding, strings_only,
                                                    errors) for arg in s])
                return str(s).encode(encoding, errors)
        elif isinstance(s, str):
            return s.encode(encoding, errors)
        elif s and encoding != 'utf-8':
            return s.decode('utf-8', errors).encode(encoding, errors)
        else:
            return s

    # 对数组排序并除去数组中的空值和签名参数
    # 返回数组和链接串
    def params_filter(self, params, is_quote=False):
        ks = list(params.keys())
        ks.sort()
        newparams = {}
        prestr = ''
        for k in ks:
            v = params[k]
            k = self.smart_str(
                k, self.settings.get("alipay_input_charset", "utf-8"))
            if k not in (b'sign', b'sign_type') and v != '':
                newparams[k] = self.smart_str(
                    v, self.settings.get("alipay_input_charset", "utf-8"))
                if is_quote:
                    prestr += '%s="%s"&' % (k, newparams[k])
                else:
                    prestr += '%s=%s&' % (k, newparams[k])

        prestr = prestr[:-1]
        return newparams, prestr

    # 生成签名结果
    def build_mysign(self, prestr, sign_type='MD5'):
        if sign_type == 'MD5':
            return md5(prestr + self.settings["alipay_key"]).hexdigest()

        elif sign_type == "RSA":
            return self.rsa_sign(prestr)

        return ''

    def rsa_verify(self, paras, sign):
        """对签名做rsa验证"""
        pub_key = RSA.importKey(self.settings["alipay_public_key"])
        verifier = PKCS1_v1_5.new(pub_key)
        data = SHA.new(paras.encode('utf-8'))
        return verifier.verify(data, base64.b64decode(sign))

    def rsa_decrypt(self, paras):
        """对支付宝返回参数解密"""
        key = RSA.importKey(self.settings["alipay_private_key"])
        key = PKCS1_OAEP.new(key)
        decrypted = key.decrypt(base64.b64decode(paras.get('notify_data')))
        paras['notify_data'] = decrypted
        return paras

    def rsa_sign(self, data):
        key = RSA.importKey(self.settings["alipay_private_key"])
        h = SHA.new(data.encode('utf-8'))
        signer = PKCS1_v1_5.new(key)
        return quote_plus(base64.b64encode(signer.sign(h)))

    def create_ws_mobile_pay(self, out_trade_no, subject, body, total_fee,
                             notify_url=None, show_url=None):
        """无线快捷收款 """

        params = {}

        # 基本参数
        params['service'] = 'mobile.securitypay.pay'
        params['partner'] = self.settings["alipay_partner"]
        params['_input_charset'] = "utf-8"
        params['seller_id'] = self.settings["alipay_seller_email"]

        params['notify_url'] = notify_url

        # 业务参数
        params['out_trade_no'] = out_trade_no  # 请与贵网站订单系统中的唯一订单号匹配

        # 订单名称，显示在支付宝收银台里的“商品名称”里，显示在支付宝的交易管理的“商品名称”的列表里。
        params['subject'] = subject

        # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
        params['body'] = body
        params['payment_type'] = '1'

        params['total_fee'] = "%0.2f" % total_fee    # 订单总金额，显示在支付宝收银台里的“应付总额”里
        params['quantity'] = 1                       # 商品的数量
        params['show_url'] = show_url

        params['it_b_pay'] = "12h"

        params, prestr = self.params_filter(params, is_quote=True)

        params['sign'] = self.build_mysign(
            prestr, self.settings["alipay_sign_type"])
        params['sign_type'] = self.settings["alipay_sign_type"]

        return '%s&sign="%s"&sign_type="%s"' % (prestr, params['sign'], params['sign_type'])

    def alipay_refund_fastpay(self, refund_date, batch_no, orders, notify_url=None):
        """生成退款链接
        """

        sign_type = "MD5"  # self.settings["alipay_sign_type"]

        params = {}

        # 基本参数
        params['service'] = 'refund_fastpay_by_platform_pwd'
        params['partner'] = self.settings["alipay_partner"]
        params['_input_charset'] = "utf-8"
        params['seller_email'] = self.settings["alipay_seller_email"]

        if notify_url:
            params['notify_url'] = notify_url

        # 业务参数
        # 退款请求的当前时间。格式为:yyyy-MM-dd hh:mm:ss。
        params['refund_date'] = refund_date
        # 退款批次号格式为:退款日期(8 位)+流水号(3~24 位)
        params['batch_no'] = batch_no
        params['batch_num'] = str(len(orders))   # 总笔数
        params['detail_data'] = "#".join(orders)

        params, prestr = self.params_filter(params, is_quote=False)

        params['sign'] = self.build_mysign(prestr, sign_type)
        params['sign_type'] = sign_type

        return self._REFUND_GATEWAY + urlencode(params)

    def notify_verify(self, post):

        # 初级验证--签名
        _, prestr = self.params_filter(post)

        sign_type = post.get("sign_type", "")
        if not sign_type and post.get("sec_id", None):
            sign_type = "RSA" if post.get("sec_id") == "001" else "MD5"

        if sign_type == "MD5":
            mysign = self.build_mysign(prestr, sign_type)
            if mysign != post.get('sign'):
                return False

        else:
            return self.rsa_verify(prestr, post.get('sign'))

        return True
