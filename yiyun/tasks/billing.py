import logging
import datetime
from yiyun.core import celery, current_app
from yiyun.libs.wxpay import WxPay
from yiyun.models import TeamOrder


@celery.task
def test_delay(arg):
    logging.error(arg * 10)


@celery.task
def refund(order_no, refund_fee, is_retry=False):
    """
    Args:
        order_no: int, 订单号
        refund_fee: 退款金额
    """

    wxpay = WxPay(appid=current_app.settings["wxpay_appid"],
                  mch_id=current_app.settings["wxpay_mchid"],
                  secret_key=current_app.settings["wxpay_secret_key"],
                  ca_certs=current_app.settings["wxpay_ca_certs"],
                  client_cert=current_app.settings["wxpay_api_client_cert"],
                  client_key=current_app.settings["wxpay_api_client_key"])

    order = TeamOrder.get(order_no=order_no)
    if order.payment_method == order.OrderPaymentMethod.WXPAY.value and \
            order.refund_state in (
                TeamOrder.OrderRefundState.PARTIAL_REFUNDING.value,
                TeamOrder.OrderRefundState.PARTIAL_REFUNDED.value,
                TeamOrder.OrderRefundState.FULL_REFUNDING.value,
                TeamOrder.OrderRefundState.FULL_REFUNDED.value
            ):

        if is_retry:
            out_trade_no = 'J%s' % order.order_no
        else:
            out_trade_no = 'N%s' % order.order_no

        try:
            response = wxpay.refund(out_trade_no=out_trade_no,
                                    out_refund_no="R%s" % order.order_no,
                                    total_fee=order.total_fee,
                                    refund_fee=refund_fee,
                                    # transaction_id=order.gateway_trade_no,
                                    op_user_id=order.gateway_account)
        except Exception as e:
            logging.error("refund fail, order_no:{0} exception:{1}".format(out_trade_no, e))
            response = None

        if response and response["result_code"] == "SUCCESS":
            logging.debug(response)
            TeamOrder.update(
                refund_state=TeamOrder.OrderRefundState.FULL_REFUNDED.value,
                refunded_fee=refund_fee,
                refunded_time=datetime.datetime.now(),
                state=TeamOrder.OrderState.TRADE_CLOSED,
            )\
                .where(TeamOrder.order_no == order.order_no)\
                .execute()

        # 换个订单号重试
        elif not is_retry:
            refund(order_no, refund_fee, is_retry=True)
        else:
            # 标记退款失败
            TeamOrder.update(
                refund_state=TeamOrder.OrderRefundState.FULL_REFUND_FAILED.value,
            ).where(TeamOrder.order_no == order.order_no)\
                .execute()

            logging.error("refund fail,order_no:{0} response:{1}".format(order_no, response))
