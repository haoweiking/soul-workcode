"""
订单接口
"""
from yiyun.models import Team, TeamOrder


class OrderService(object):

    @classmethod
    def new_order(cls, amount, team, user, order_type, payment,
                  activity_id, title, **kwargs):
        order = TeamOrder.create(order_no=TeamOrder.get_new_order_no(),
                                 team=team,
                                 user=user,
                                 order_type=order_type,
                                 payment_method=payment,
                                 payment_fee=amount,
                                 total_fee=amount,
                                 activity_id=activity_id,
                                 title=title,
                                 **kwargs
                                 )
        return order

    @classmethod
    def can_continue_pay(cls, order):
        """
        检查订单是不是需要支付
        Args:
            order:

        Returns:

        """
        if order.state >= 1:
            return False
        return True
