

import hashlib
import base64
import logging
import json
from datetime import datetime

import requests


class CloopenError(Exception):
    """docstring for CloopenError"""
    pass


class Cloopen(object):
    """docstring for Cloopen"""

    def __init__(self, account_sid, auth_token, app_id, is_sandbox=False):

        if is_sandbox:
            self.base_url = "https://sandboxapp.cloopen.com:8883/2013-12-26"

        else:
            self.base_url = "https://app.cloopen.com:8883/2013-12-26"

        self.account_sid = account_sid
        self.auth_token = auth_token
        self.app_id = app_id

    def get_time(self):
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def generate_sig(self, req_time):
        origin_str = "%s%s%s" % (self.account_sid, self.auth_token, req_time)
        return hashlib.md5(origin_str.encode("utf-8")).hexdigest().upper()

    def api_request(self, path, post_args=None, **kwargs):

        req_time = self.get_time()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": base64.b64encode(("%s:%s" % (self.account_sid, req_time)).encode("utf-8"))
        }

        args = {}
        if kwargs:
            args.update(kwargs)

        args['sig'] = self.generate_sig(req_time=req_time)

        url = self.base_url + ("/Accounts/%s" % self.account_sid) + path

        if post_args:
            r = requests.post(url, params=args, data=json.dumps(post_args),
                              headers=headers, verify=False, timeout=30)

        else:
            r = requests.get(url, params=args, headers=headers,
                             verify=False, timeout=30)

        respose = json.loads(r.content.decode("utf-8"))
        if r.status_code != 200 or respose.get("statusCode", None) != '000000':

            if respose['statusCode'] == '160021':
                error_msg = "%s 发送太快，请歇一下再试" % respose['statusCode']
            else:
                error_msg = "%s %s" % (respose['statusCode'], respose['statusMsg'])

            logging.error(error_msg)
            raise CloopenError(error_msg)

        return respose

    def send_sms(self, to, body, subaccount):

        r = self.api_request("/SMS/Messages", post_args={
            "to": to,
            "body": body,
            "msg_type": 0,
            "appId": self.app_id,
            "subAccountSid": subaccount
        })

        return r

    def send_tpl_sms(self, to, template_id, datas):

        r = self.api_request("/SMS/TemplateSMS", post_args={
            "to": to,
            "appId": self.app_id,
            "templateId": template_id,
            "datas": datas
        })

        return r
