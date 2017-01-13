import logging
import json

import requests
from yiyun.exceptions import BaseError
from tornado.auth import (escape, httpclient, urllib_parse)


class ParteamRequestError(BaseError):
    pass


class ParteamMixin(object):
    """ 派队接口 """

    def get_session(self, access_token):

        resp = self.parteam_request("/match/openapi/getUserInfo.do",
                                    post_args=dict(
                                        ptToken=access_token,
                                        version=1
                                    ))

        return resp['userInfo']

    def parteam_request(self, path, post_args=None, **args):

        url = self.settings['parteam_api_url'].rstrip("/") + path
        all_args = {}
        all_args.update(args)

        if all_args:
            url += "?" + urllib_parse.urlencode(all_args)

        try:
            if post_args is not None:
                r = requests.post(url,
                                  data=json.dumps(post_args),
                                  timeout=5,
                                  headers={"Content-Type": "application/json"
                                           })

            else:
                r = requests.get(url, timeout=5)

        except Exception as e:
            raise ParteamRequestError(500, "请求派队接口失败",
                                      log_message="Parteam Req Error: {0}".format(e))

        if 200 > r.status_code > 299:
            raise ParteamRequestError(
                r.status_code, "请求派队接口失败",
                log_message="Parteam Req Error: ({0}){1}".
                format(r.status_code, r.content))

        try:
            resp = r.json()
        except Exception as e:
            raise ParteamRequestError(
                r.status_code, "请求派队接口失败",
                log_message="Parteam Resp Parse Error: {0}".format(e))

        if resp['code'] == 600:
            raise ParteamRequestError(
                r.status_code, resp['message'],
                log_message="Parteam Resp Parse Error: {0}".format(resp))

        if resp['code'] != 200 \
                or 'attribute' not in resp:
            raise ParteamRequestError(
                r.status_code, "请求派队接口失败",
                log_message="Parteam Resp Parse Error: {0}".format(resp))

        return resp['attribute']
