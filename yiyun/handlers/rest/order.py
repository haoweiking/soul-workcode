from typing import Union
import logging
import datetime

from tornado import gen
from peewee import prefetch
import xmltodict

import tornado.web

from yiyun.consts import PaymentMethod
from yiyun.libs.wxpay import WxPayMixin
from yiyun.libs.alipay import AlipayMixin
from yiyun.libs.peewee_filter import Filter, ForeignKeyFiltering
from yiyun.models import User, Team, TeamOrder, Activity, Sport, ActivityMember
from .base import (BaseClubAPIHandler, rest_app, ApiException, authenticated,
                   ApiBaseHandler)
from .serializers.order import SecureOrderSerializer


class RefreshOrderPaymentMixin(object):
    """
    刷新支付方式
    """

    def check_order_state(self, order: TeamOrder):
        """
        检查订单支付状态

        Raises:
            1. 状态大于等于 WAIT_PA_RETURN (已支付的订单) 无法生成二维码;
            HTTPError(400, '订单已支付')
            2. 状态小于 WAIT_BUYER_PAY (关闭的订单) 无法生成二维码
            HTTPError(400, '订单已关闭')

        Args:
            order: TeamOrder

        Returns: bool

        """
        if order.state < TeamOrder.OrderState.WAIT_BUYER_PAY:
            raise ApiException(400, '订单已关闭')

        if order.state >= TeamOrder.OrderState.WAIT_PAY_RETURN:
            raise ApiException(400, '订单已支付')


@rest_app.route(r'/orders/wxpay/unifiedorder')
class WxpayUnifiedOrder(WxPayMixin, RefreshOrderPaymentMixin, ApiBaseHandler):
    """ 微信支付统一下单接口
    """

    @authenticated
    @gen.coroutine
    def post(self):

        order_no = self.get_argument('order_no', None)
        trade_type = self.get_argument("trade_type", "jsapi")

        if trade_type.upper() not in ("NATIVE", "JSAPI"):
            raise ApiException(400, '交易类型不支持')

        order = TeamOrder.get_or_404(order_no=order_no, user=self.current_user)

        self.check_order_state(order)

        wx_order = yield self.handle_wxpay(order,
                                           trade_type=trade_type.upper(),
                                           body=order.title
                                           )

        self.write(wx_order)


@rest_app.route(r"/orders/payment/alipay/(\d+)")
class AlipayOrder(AlipayMixin, RefreshOrderPaymentMixin, ApiBaseHandler):
    """
    获取支付宝支付信息
    """

    @authenticated
    def post(self, order_no):
        order = TeamOrder.get_or_404(order_no=order_no, user=self.current_user)

        self.check_order_state(order)
        notify_url = ""
        paystr = self.create_ws_mobile_pay(
            out_trade_no=order.order_no, subject=order.title, body=order.title,
            total_fee=order.payment_fee, notify_url=notify_url)
        self.write({"paystr": paystr})


class TeamOrderCallbackMixin(object):

    def check_state(self, order: TeamOrder):
        """
        校验订单状态
        :param order:
        :return:
        """
        if order.state >= TeamOrder.OrderState.WAIT_BUYER_PAY.value or \
                order.state <= TeamOrder.OrderState.WAIT_PAY_RETURN.value:
            return True
        raise ApiException(422, "订单已支付无需重复支付")

    def get_order(self, order_no: str) -> Union[TeamOrder, None]:
        """
        获取 TeamOrder
        :param order_no:
        :return:
        """
        try:
            order = TeamOrder.select()\
                .where(TeamOrder.order_no == order_no)\
                .get()
        except TeamOrder.DoesNotExist:
            msg = "订单不存在"
            logging.error(msg)
            order = None
        return order

    def _finish_order(self, order: TeamOrder, arguments: dict,
                      payment: PaymentMethod):
        """
        完成支付流程
        Args:
            order: TeamOrder
            arguments: dict, 微信服务器回调的 body
            payment: PaymentMethod, 支付方式

        Returns:

        """

        logging.debug('开始终结支付订单[{0}]'.format(order.order_no))
        if payment == PaymentMethod.ALIPAY:
            # 支付宝
            gateway_account = arguments["buyer_email"]
            gateway_trade_no = arguments["trade_no"]
        else:
            # 默认违心支付
            gateway_trade_no = arguments['transaction_id']
            gateway_account = arguments['openid']

        TeamOrder.update(state=TeamOrder.OrderState.TRADE_BUYER_PAID,
                         paid=datetime.datetime.now(),
                         gateway_trade_no=gateway_trade_no,
                         gateway_account=gateway_account) \
            .where(TeamOrder.order_no == order.order_no) \
            .execute()
        ActivityMember \
            .update(payment_method=payment.value,
                    payment_state=TeamOrder.OrderState.TRADE_BUYER_PAID,
                    state=ActivityMember.ActivityMemberState.confirmed,
                    paid=datetime.datetime.now(),
                    confirmed=datetime.datetime.now()) \
            .where(ActivityMember.activity == order.activity_id) \
            .execute()

        # 更新活动成员数
        Activity.update_members_count(order.activity_id)


@rest_app.route(r'/orders/callback/wxpay', name='api_wxpay_callback')
class WxpayOrderCallbackHandler(WxPayMixin, TeamOrderCallbackMixin,
                                ApiBaseHandler):
    """
    微信支付异步回调接口
    """
    verify_sign = False

    def post(self, *args, **kwargs):
        xml_body = self.request.body
        body = xmltodict.parse(xml_body)['xml']
        # if not self.validate_wxpay_body(body):
        #     logging.warning('支付回调签名错误, 可能来自非微信服务器')
        #     raise ApiException(403, '权限错误')
        return_code = body.get('return_code')
        if return_code == 'SUCCESS':
            out_trade_no = body['out_trade_no'][1:]
            logging.debug('订单号码: [{0}] -> [{1}]'
                          .format(body['out_trade_no'], out_trade_no))
            order = self.get_order(order_no=out_trade_no)
            if not order:
                self.return_success_xml()
            else:
                self.check_state(order)
                self._finish_order(order, body, PaymentMethod.WXPAY)
                self.return_success_xml()
        else:
            logging.debug(body)
            raise ApiException(400, '支付回调失败')

    def validate_wxpay_body(self, body):
        """
        校验微信发来的信息签名是不是正确
        Args:
            body:

        Returns:

        """
        logging.debug(body)
        sign = body.pop('sign', None)
        actually_sign = self.wxpay.sign_params(body, key=self.wxpay.secret_key)
        return sign == actually_sign

    def return_success_xml(self):

        # TODO: 返回成功
        _params = {
            'xml': {
                'return_code': 'SUCCESS',
                'return_msg': 'OK'
            }
        }
        xml = xmltodict.unparse(_params)
        logging.debug(xml)
        self.write(xml)


@rest_app.route("/orders/callback/alipay")
class AlipayOrderCallbackHandler(AlipayMixin, TeamOrderCallbackMixin,
                                 ApiBaseHandler):
    """
    支付宝支付回调接口
    """

    def get_parsed_body(self) -> dict:
        """
        解析支付宝请求的 body
        :return:
        """
        logging.debug("支付宝回调通知: {0}".format(self.request.arguments))

        arguments = {}
        for key in self.request.arguments.keys():
            arguments[key] = self.get_argument(key)

        logging.debug("已解析的回调通知: {0}".format(arguments))
        return arguments

    def post(self):
        body = self.get_parsed_body()

        if not self.notify_verify(body):
            self.logger.info("notify verify fail")
            raise tornado.web.HTTPError(
                403, log_message="通知信息签名校验失败, 消息可能来自非支付宝服务器")

        order = self.get_order(order_no=body["out_trade_no"])
        if order:
            self.check_state(order)
            self._finish_order(order=order, arguments=body,
                               payment=PaymentMethod.ALIPAY)
            self.write("success")


class OrderFilter(Filter):
    team_id = ForeignKeyFiltering(source="team", foreign_field="id")

    class Meta:
        fields = ("team_id", "state",)


@rest_app.route(r"/users/self/orders")
class UserOrderHandler(BaseClubAPIHandler):
    """获取用户订单"""

    filter_classes = (OrderFilter,)

    @authenticated
    def get(self):
        """当前登录用户的订单列表"""
        query = TeamOrder.select(
            TeamOrder,
            Activity
        ).join(
            Activity, on=(Activity.id == TeamOrder.activity_id).alias(
                "activity")
        ).where(TeamOrder.user == self.current_user) \
            .order_by(TeamOrder.id.desc())

        query = self.filter_query(query)
        page = self.paginate_query(query)
        data = self.get_paginated_data(page=page, alias="orders",
                                       serializer=SecureOrderSerializer)

        self.write(data)


@rest_app.route(r'/orders/([\d]+)/state')
class OrderStateHandler(ApiBaseHandler):
    """
    返回订单状态
    """

    @authenticated
    def get(self, order_no):
        order = TeamOrder.get_or_404(order_no=order_no)

        self.write({
            "order_no": order.order_no,
            "team_id": order.team_id,
            "state": TeamOrder.OrderState(order.state).name
        })


@rest_app.route(r"/users/self/orders/(\d+)")
class UserOrderDetailHandler(BaseClubAPIHandler):
    """订单详情"""

    @authenticated
    def get(self, order_no):
        # order = TeamOrder.get_or_404(user=self.current_user,
        #                              order_no=order_no)
        try:
            order = TeamOrder.select(TeamOrder, Activity)\
                .join(Activity, on=(TeamOrder.activity_id == Activity.id)
                      .alias("activity"))\
                .where(TeamOrder.user == self.current_user,
                       TeamOrder.order_no == order_no)
            user = User.select().where(User.id == self.current_user.id)
            team = Team.select()
            order_pf = prefetch(order, user, team).get()
        except TeamOrder.DoesNotExist:
            raise ApiException(404, "订单不存在")

        self.write(SecureOrderSerializer(instance=order_pf).data)
