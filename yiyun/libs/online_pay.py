import logging
from .wxpay import WxPayMixin
from .alipay import AlipayMixin


class AlipayHandlerMixin(AlipayMixin):

    def handle_alipay(self, pre_order, *args, **kwargs):
        """
        生成支付宝订单
        Args:
            pre_order: 预支付订单
            *args:
            **kwargs:

        Returns:

        """
        # TODO: 完成支付宝调用
        notify_url = urljoin(self.request.full_url(),
                             self.reverse_url('api_alipay_callback'))

        consume_info = pre_order.get_info()

        if getattr(pre_order, 'use_credit', False):
            total_fee = pre_order.amount - self.current_user.credit
        else:
            total_fee = pre_order.amount
        logging.debug('支付宝支付 total_fee: [{0}]'.format(total_fee))

        alipay = self.create_ws_mobile_pay(
            out_trade_no=pre_order.order_number,
            subject='商品描述',
            body='商品详情',
            total_fee=total_fee,
            notify_url=notify_url,
            show_url=None,
        )

        consume_info['alipay'] = alipay
        self.write(consume_info)


class OnlinePayMixin(AlipayHandlerMixin, WxPayMixin):
    pass
