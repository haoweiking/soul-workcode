"""
派队接口
"""

import time
from typing import Dict
import logging
import json
from enum import Enum
import requests
from yiyun.core import current_app as app


class ParteamRequestError(Exception):
    """派队接口请求异常"""
    pass


class RefundError(Exception):
    """退款错误"""
    pass


class NotPaidError(RefundError):
    """订单未支付"""
    pass


class ParteamUser(object):
    """
    派队用户 Model
    TODO: 可改进实现 metaclass
    """
    def __init__(self, user_info: dict):
        self.id = user_info["userId"]
        self.nickName = user_info["nickName"]
        self.ptToken = user_info["ptToken"]
        self.userHeadPicUrl = user_info["userHeadPicUrl"]
        self.userId = user_info["userId"]

        # 当作可选字段来处理
        self.birthday = user_info.get("birthday", "")
        self.gender = user_info.get("gender", "")
        self.mobile = user_info.get("mobile", "")

    @property
    def gender_text(self):
        if self.gender == 0:
            return "男"
        elif self.gender == 1:
            return "女"
        else:
            return "未知"

    @property
    def avatar_url(self):
        if self.userHeadPicUrl:
            return "%s%s" % (app.settings["parteam_avatar_base_url"],
                             self.userHeadPicUrl)
        else:
            # TODO 一个默认头像
            return ""

    @property
    def dob(self):
        # 没有时区信息 默认转换成本地时间
        try:
            birthday = time.localtime(float(self.birthday/1000))
        except ValueError:
            return ""
        else:
            return time.strftime('%Y-%m-%d %H:%M:%S', birthday)

    @property
    def age(self):
        try:
            birthday = time.localtime(float(self.birthday/1000))
            now = time.localtime(time.time())
        except ValueError:
            return ""

        try:
            year_of_now = int(time.strftime('%Y', now))
            year_of_dob = int(time.strftime('%Y', birthday))
            age = year_of_now - year_of_dob

            if age < 0:
                return ""
            else:
                return age
        except ValueError:
            return ""

    @property
    def secure_info(self):
        info = {
            "nickName": self.nickName,
            "userHeadPicUrl": self.userHeadPicUrl,
            "userId": self.userId,
            "mobile": self.mobile,
            "gender": self.gender,
            "birthday": self.birthday
        }
        return info


class PushType(Enum):
    """
    MATCH_PAY_SUCCESS: 支付成功推送
    MATCH_START  赛事开始前两小时提醒推送
    MATCH_PUBLISH_SCHEDULE: 赛事方发布赛程推送
    MATCH_SPONSOR_REFUND: 主办方发起退款推送
    """
    match_pay_success = "MATCH_PAY_SUCCESS"
    match_start = "MATCH_START"
    match_publish_schedule = "MATCH_PUBLISH_SCHEDULE"
    match_sponsor_refund = "MATCH_SPONSOR_REFUND"


class ParteamPushMessage(object):
    pushType = None  # type: PushType
    _body = {}  # type: dict

    def __init__(self, user_infos: list, match_id: int, match_name: str,
                 sponsor_name: str, sponsor_pic_url: str):
        """
        派队赛事推送消息
        :param user_infos:
        :param match_id:
        :param match_name:
        :param sponsor_name:
        :param sponsor_pic_url:
        """
        self._body["userInfos"] = user_infos
        self._body["matchId"] = match_id
        self._body["matchName"] = match_name
        self._body["sponsorName"] = sponsor_name
        self._body["sponsorPicUrl"] = sponsor_pic_url
        self._body["pushType"] = self.pushType.value

    @property
    def body(self):
        """消息内容"""
        return self._body


class JoinMatchDone(ParteamPushMessage):
    """
    参赛支付成功消息
    """
    pushType = PushType.match_pay_success

    def __init__(self, match_fee: int, *args, **kwargs):
        self._body["matchFee"] = match_fee
        super(JoinMatchDone, self).__init__(*args, **kwargs)


class MatchStartMessage(ParteamPushMessage):
    """
    赛事即将开始发送消息
    """
    pushType = PushType.match_start


class NewMatchScheduleMessage(ParteamPushMessage):
    """新赛程消息"""
    pushType = PushType.match_publish_schedule


class RefundMessage(ParteamPushMessage):
    """主办方退款"""
    pushType = PushType.match_sponsor_refund

    def __init__(self, order_no: str, *args, **kwargs):
        self._body["orderNo"] = order_no
        super(RefundMessage, self).__init__(*args, **kwargs)


class Parteam(object):

    def __init__(self, host: str):
        self.host = host

    def do_request(self, path: str, data: dict) -> dict:
        url = self.host.rstrip("/") + path
        logging.debug("请求地址: {0}".format(url))

        body = {"version": 1}
        body.update(data)
        logging.debug("请求 body: {0}".format(body))

        req = requests.post(url, data=json.dumps(body), timeout=10,
                            headers={"Content-Type": "application/json"})

        if req.status_code > 299 or req.status_code < 200:
            logging.debug(req.content)
            raise ParteamRequestError("接口调用异常 HTTPStatus: {0}"
                                      .format(req.status_code))

        resp = req.json()
        logging.debug("返回数据: {0}".format(resp))

        if (resp["code"] > 299 or req.status_code < 200) \
                and resp["code"] not in \
                        [1001, 1002, 1003, 1004, 1005, 1006, 1007]:
            # Fuck Business Code [1001, 1002, 1003, 1004]
            raise ParteamRequestError("获取数据失败: {0}"
                                      .format(resp["message"]))

        return resp

    def parteam_user(self, user_ids: list) -> Dict[int, ParteamUser]:
        """
        批量获取派队用户信息
        :param user_ids:
        :return:
        """
        path = "/match/openapi/getUserInfoList.do"

        assert user_ids, "`user_ids` 不能为空"

        uid_str = ",".join(map(str, user_ids))
        resp = self.do_request(path, {"userIds": uid_str})
        user_list = resp["attribute"]["userInfoList"]

        users = dict()
        for user in user_list:
            users[int(user["userId"])] = ParteamUser(user)
        return users

    def order_refund(self, user_id: int, order_no: str, refund_fee: int,
                     notify_url: str=None, role: int=1) -> bool:
        """
        调用退款接口

        调用退款后同步返回处理结果
        {
            code: 状态, 200=成功， 1001=订单生成失败， 1002=退款失败，
                    1003=没有该订单, 1004=申请退款人与支付人不一致,
                    1005=该订单不是已支付状态, 1006=退款数额不能大于付款数额 ，
                    1007=必须是赛事订单可以退款
            "message": 返回消息
        }
        :param user_id:
        :param order_no:
        :param refund_fee: int 退款金额, 单位 `分`
        :param notify_url:
        :param role: 申请退款角色 1: 用户, 2: 赛事方
        :return: bool, 接口调用是否成功
        """
        path = "/match/openapi/applyRefundOrder.do"
        data = {
            "applyRefundOrderType": role,
            "orderNo": order_no,
            "refundTotalFee": refund_fee,
            "userId": user_id
        }
        if notify_url:
            data["notifyUrl"] = notify_url

        resp = self.do_request(path=path, data=data)

        if resp["code"] == 200:
            return True

        if resp["code"] == 1005:
            msg = "Code: {0}, Message: {1}"\
                .format(resp["code"], resp["message"])
            raise NotPaidError(msg)

        logging.info("调用派队退款接口失败: code: {0}, message: {1}"
                     .format(resp["code"], resp["message"]))
        raise RefundError("退款失败: {0}, {1}"
                          .format(resp["code"], resp["message"]))

    def push_message(self, message: ParteamPushMessage):
        """调用派队推送接口, 发送推送消息"""
        path = "/match/openapi/matchPush.do"
        data = message.body
        try:
            resp = self.do_request(path, data=data)
        except ParteamRequestError as e:
            logging.error(e)
            return False

        if resp["code"] == 200:
            return True

        logging.debug("调用派队消息推送接口失败: code: {0}, message: {1}"
                      .format(resp["code"], resp["message"]))
        return False

