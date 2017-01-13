"""
赛事任务
"""

import logging
from datetime import datetime

from yiyun.core import celery, current_app as app
from yiyun.libs.parteam import (Parteam, ParteamRequestError, RefundError,
                                NotPaidError)
from yiyun.models import (Team, TeamOrder, Match, SettlementApplication,
                          MatchMember)
from .match_notify import match_refund as refund_notify


@celery.task
def settlement(application_id):
    """
    清算任务
    :param application_id:
    :return:
    """
    application = SettlementApplication.get(id=application_id)  # type: SettlementApplication
    orders = TeamOrder.select()\
        .where(TeamOrder.team == application.team_id,
               TeamOrder.activity_id == application.match_id,
               TeamOrder.state == TeamOrder.OrderState.TRADE_BUYER_PAID)

    balance = 0
    order_ids = []
    for order in orders:
        balance += order.payment_fee
        order_ids.append(order.id)

    with Team._meta.database.transaction():
        Team.update(credit=Team.credit + balance)\
            .where(Team.id == application.team_id).execute()
        TeamOrder.update(state=TeamOrder.OrderState.TRADE_FINISHED.value)\
            .where(TeamOrder.id << order_ids).execute()
        Match.update(finished=datetime.now())\
            .where(Match.id == application.match_id).execute()
        SettlementApplication.update(balance=balance)\
            .where(SettlementApplication.id == application_id).execute()


@celery.task(bind=True)
def batch_refund_by_sponsor(self, match_id: int):
    """
    主办方注销赛事后退款任务
    :param self:
    :param match_id:
    :return:
    """


@celery.task(bind=True)
def batch_refund_worker(self, member_id: int):
    """
    批量退款的 worker, 调用派队的 `申请退款`接口

    退款成功后继续调用派队推送接口推送主办方取消比赛退款的消息

    :param self:
    :param member_id:
    """
    parteam = Parteam(app.settings["parteam_api_url"])
    member = MatchMember.get(id=member_id)  # type: MatchMember
    team_order = TeamOrder.get(id=member.order_id)  # type: TeamOrder
    try:
        parteam.order_refund(user_id=member.user_id, order_no=member.pt_order_no,
                             refund_fee=int(team_order.payment_fee * 100),
                             notify_url="", role=2)
    except NotPaidError:
        TeamOrder.update(state=TeamOrder.OrderState.TRADE_CLOSED_BY_USER) \
            .where(TeamOrder.id == team_order.id).execute()
    except ParteamRequestError as e:
        msg = "主办方取消比赛调用派队退款申请接口错误: error: {0}\nmatch_id={1}, " \
              "pt_order_no={2}"\
            .format(str(e), member.match_id, member.pt_order_no)
        logging.error(msg)
        self.retry(exc=e)
    else:
        TeamOrder.update(state=TeamOrder.OrderState.TRADE_CLOSED,
                         refund_state=TeamOrder.OrderRefundState
                         .FULL_REFUNDED.value)\
            .where(TeamOrder.id == team_order.id).execute()

        user_info = {"mobile": member.mobile, "userId": member.user_id}
        refund_notify.delay(match_id=member.match_id,
                            order_no=member.pt_order_no, user_info=user_info)
