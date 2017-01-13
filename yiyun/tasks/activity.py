
import json
import copy
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from dateutil.relativedelta import relativedelta

from yiyun.core import celery, current_app as app
from yiyun.models import (fn, Activity, ActivityMember,
                          Team, TeamOrder, TeamAccountLog)

from yiyun.exceptions import ArgumentError


@celery.task
def update_activity(activity_id):
    pass


@celery.task
def cancel_activity(activity_id, cancel_reason=""):
    """取消活动
        1. 取消活动后需要通知用户活动取消，已付款用户将退款
        2. 已结算活动不能取消
    """

    activity = Activity.get_or_404(id=activity_id)

    if activity.state == Activity.ActivityState.finished:
        raise ArgumentError(400, "已结束活动不能取消")

    members = ActivityMember.select().where(
        ActivityMember.activity == activity_id
    )

    with app.db.transaction() as txn:
        for member in members:
            member.refund("活动取消")

        # 修改场次状态为取消
        Activity.update(
            state=Activity.ActivityState.cancelled,
            cancelled=datetime.now(),
            cancel_reason=cancel_reason,
            online_paid_amount=Decimal(0),
            credit_paid_amount=Decimal(0),
            cash_paid_amount=Decimal(0),
            free_times_amount=Decimal(0)
        ).where(
            Activity.id == activity.id
        ).execute()

        # TODO: 通知用户活动场次被取消


@celery.task
def finish_activities():
    """定时执行结算完成的场次
    """

    activities = Activity.select().where(
        (Activity.state == Activity.ActivityState.opening.value
         ) & (Activity.end_time <= datetime.now())
    )

    for activity in activities:
        finish_activity.delay(activity.id)


@celery.task
def finish_activity(activity_id):
    """结算活动场次

        1. 将用户在线支付费用转到俱乐部账户
        2. 标记场次和订单状态为完成
        3. 记录俱乐部账户变化
    """

    activity = Activity.get_or_404(id=activity_id)

    if activity.end_time > datetime.now():
        raise Exception("活动场次未结束")

    if activity.state == Activity.ActivityState.cancelled:
        raise Exception("活动场次已取消")

    if activity.state == Activity.ActivityState.finished:
        raise Exception("活动场次已结算")

    # 计算在线支付完成交易的总额
    online_paid_amount = TeamOrder.select(
        fn.SUM(TeamOrder.payment_fee)
    ).where(
        TeamOrder.activity_id == activity_id,
        TeamOrder.state >= TeamOrder.OrderState.TRADE_BUYER_PAID.value,
        TeamOrder.refund_state == TeamOrder.OrderRefundState.NO_REFUND,
        TeamOrder.payment_method << TeamOrder.ONLINE_PAYMENT_METHODS
    ).scalar() or 0

    # 计算余额支付完成交易的总额
    credit_paid_amount = TeamOrder.select(
        fn.SUM(TeamOrder.credit_fee)
    ).where(
        TeamOrder.activity_id == activity_id,
        TeamOrder.state >= TeamOrder.OrderState.TRADE_BUYER_PAID.value
    ).scalar() or 0

    # 使用次数
    free_times_amount = ActivityMember.select(
        fn.SUM(ActivityMember.free_times)
    ).where(
        ActivityMember.state == ActivityMember.ActivityMemberState.confirmed
    ).scalar() or 0

    # online_paid_amount= DecimalField(default=Decimal(0), verbose_name="在线支付收入")
    # credit_paid_amount= DecimalField(default=Decimal(0), verbose_name="余额支付收入")
    # cash_paid_amount= DecimalField(default=Decimal(0), verbose_name="现金支付收入")
    # free_times_amount = IntegerField(default=0, verbose_name="次卡支付数量")

    with app.db.transaction() as txn:
        team = Team.select().where(
            Team.id == activity.team.id
        ).for_update().get()

        # 将收入打到俱乐部账上
        Team.update(
            credit=Team.credit + online_paid_amount,
            total_receipts=Team.total_receipts + online_paid_amount,
            updated=datetime.now()
        ).where(
            Team.id == team.id
        ).execute()

        # 将订单修改状态为已完成
        TeamOrder.update(
            state=TeamOrder.OrderState.TRADE_FINISHED.value,
            finished=datetime.now()
        ).where(
            TeamOrder.activity_id == activity_id,
            TeamOrder.state == TeamOrder.OrderState.TRADE_BUYER_PAID.value,
            TeamOrder.refund_state == TeamOrder.OrderRefundState.NO_REFUND.value
        ).execute()

        # 修改场次状态为已结算
        Activity.update(
            state=Activity.ActivityState.finished,
            finished=datetime.now(),
            online_paid_amount=online_paid_amount,
            credit_paid_amount=credit_paid_amount,
            free_times_amount=free_times_amount
        ).where(
            Activity.id == activity_id
        ).execute()

        # 记录俱乐部账户变更
        TeamAccountLog.create(
            team_id=team.id,
            credit_change=online_paid_amount,
            change_type=0,
            credit_before=team.credit,
            credit_after=team.credit + online_paid_amount,
            note="活动结算：%s(%s)" % (activity.title, activity.start_time),
            activity_id=activity_id,
            operator_id=0
        )

    # 生成下期活动
    gen_next_activity(activity_id)

    # TODO 发短信告之俱乐部主活动结算有收入了


def gen_next_activity(activity_id):
    """ 生成下期活动
    """

    if Activity.select().where(
        Activity.parent_id == activity_id
    ).exists():
        logging.debug("已经存在")
        return

    activity = Activity.get_or_404(id=activity_id)

    # 时间相关都顺延一周
    delta = timedelta(days=7)

    if activity.repeat_end and \
            datetime.now() + delta > activity.repeat_end:
        logging.debug("活动已经结束自动循环")
        return

    activity = copy.copy(activity)

    activity.id = None
    activity.members_count = 0
    activity.comments_count = 0
    activity.recommend_time = 0
    activity.recommend_region = 0

    if activity.join_start:
        activity.join_start += delta

    if activity.join_end:
        activity.join_end += delta

    activity.cancelled = None
    activity.cancel_reason = ""
    activity.finished = None

    activity.start_time += delta
    activity.end_time += delta

    activity.online_paid_amount = 0
    activity.credit_paid_amount = 0
    activity.cash_paid_amount = 0
    activity.free_times_amount = 0

    activity.created = datetime.now()
    activity.updated = datetime.now()

    activity.state = Activity.ActivityState.opening
    activity.parent_id = activity_id
    activity.save()

    # 更新俱乐部活动数
    Team.update_activities_count(activity.team_id)
