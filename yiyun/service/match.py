from typing import Union
from datetime import timedelta, datetime
import logging

import qrcode
from peewee import SelectQuery
from yiyun.libs.parteam import Parteam, RefundError, NotPaidError
from yiyun.core import current_app as app
from yiyun.models import (User, Admin, Match, MatchStatus, MatchComment,
                          TeamOrder, MatchStatusLike, MatchMember,
                          MatchStartCeleryTask, SettlementApplication,
                          ApplicationState)
from .base import BaseService


MatchMemberState = MatchMember.MatchMemberState


class MatchException(Exception):
    pass


class MatchStateError(MatchException):
    """赛事状态错误"""
    pass


class SettlementApplicationException(MatchException):
    """结算申请异常"""
    pass


class SettlementApplicationExist(SettlementApplicationException):
    """赛事结算申请已存在"""
    pass


class ApplicationProcessingException(SettlementApplicationException):
    """结算申请进度异常"""
    pass


class MatchService(BaseService):

    @classmethod
    def cancel(cls, match: Match, user: User):
        """
        主办方取消赛事
        :param match:
        :param user:
        :return:
        """
        from yiyun.tasks.match import batch_refund_worker
        if not match.can_cancel():
            raise MatchStateError("当前赛事状态无法取消: {0}"
                                  .format(match.state))

        with cls.database.transaction():
            Match.update(state=Match.MatchState.cancelled.value)\
                .where(Match.id == match.id).execute()

            members = MatchMember.select()\
                .where(MatchMember.match_id == match.id,
                       MatchMember.state >= MatchMember.MatchMemberState.wait_pay.value,
                       MatchMember.state <= MatchMember.MatchMemberState.normal.value)
            for member in members:
                batch_refund_worker.delay(member_id=member.id)

    @classmethod
    def join(cls, user_id, match: Union[int, Match]):
        """加入赛事"""

    @classmethod
    def leave(cls, user_id, match: Match, notify_url: str=None, insists=False,
              role: int=1):
        """
        退出赛事

        :param user_id:
        :param match:
        :param notify_url: 派队回调地址
        :param insists: 强制退出
        :param role: 退赛发起人, 1 用户, 2 赛事方
        :return:
        """
        logging.debug("notify_url: {0}, insists: {1}"
                      .format(notify_url, insists))

        if not insists and notify_url is None:
            raise AssertionError("非强制退出 `insists=False` 操作需要提供退款回调"
                                 "地址 `notify_url`")

        if insists is False and not match.can_leave():
            raise MatchException("赛事无法退出")

        # 退出赛事
        member = MatchMember.get(user_id=user_id, match_id=match.id)  # type: MatchMember
        with Match._meta.database.transaction():
            if insists:
                match.leave(member)

            # Warning: 数据库事物中尝试远程 HTTP 调用, 需要修复
            else:
                # match.leave_request(member)
                # 调用退款接口
                pt = Parteam(app.settings["parteam_api_url"])
                if member.order_id:
                    # 有支付信息, 调用退款接口
                    order = TeamOrder.get(id=member.order_id)  # type: TeamOrder
                    refund_fee = int(order.payment_fee * 100)
                    try:
                        pt.order_refund(user_id=user_id,
                                        order_no=member.pt_order_no,
                                        refund_fee=refund_fee,
                                        notify_url=notify_url,
                                        role=role)
                    except NotPaidError as e:
                        logging.warning("调用派队退款接口发现订单未支付: {0}"
                                        .format(str(e)))
                        TeamOrder.update(state=TeamOrder.OrderState
                                         .TRADE_CLOSED_BY_USER.value) \
                            .where(TeamOrder.id == member.order_id) \
                            .execute()
                        match.leave(member)
                    except RefundError as e:
                        raise MatchException(e)
                    else:
                        # 更新订单状态为 `退款`, 订单退款状态为 `全部退款`
                        TeamOrder.update(
                            state=TeamOrder.OrderState.TRADE_CLOSED.value,
                            refund_state=TeamOrder.OrderRefundState.FULL_REFUNDED.value,
                            refunded_time=datetime.now())\
                            .where(TeamOrder.id == member.order_id)\
                            .execute()
                        match.leave(member)
                else:
                    # 无支付信息直接退赛
                    match.leave(member)

    @classmethod
    def members(cls, match: Match, state: Union[None, MatchMemberState]=None)\
            -> SelectQuery:
        """
        获取赛事参赛成员
        :param match: Match, 赛事
        :param state: MatchMember.MatchMemberState, 过滤参赛成员状态
        :return: SelectQuery
        """
        query = MatchMember.select().where(MatchMember.match_id == match.id)
        if state:
            query = query.where(MatchMember.state == state.value)
        return query

    @classmethod
    def add_match_start_notify(cls, match: Match):
        """
        调用 celery.task 添加比赛开始通知, 任务在比赛开始前 2 小时执行;
        如果发现已添加会自动取消之前的通知任务, 并重新添加新推送任务
        :param match:
        :return:
        """
        raise DeprecationWarning("接口废弃, celery task 任务确认机制的原因, "
                                 "不适合用来做长期的定时任务")
        # from yiyun.tasks.match_notify import match_start
        #
        # MatchStartCeleryTask.terminate_if_necessary(match_id=match.id)
        #
        # task_id = match_start.apply_async(
        #     (match.id,), eta=match.start_time - timedelta(hours=2))
        #
        # logging.debug("call add_match_start_notify: %s" % match.id)
        # MatchStartCeleryTask.new_task(task_id, match.id)

    @classmethod
    def add_match_status_notify(cls, match: Match):
        """
        主办方发布新赛程后调用, 添加消息推送任务
        :param match:
        :return:
        """
        from yiyun.tasks.match_notify import new_match_status

        logging.debug("call add_match_status_notify: %s" % match.id)        
        new_match_status.delay(match_id=match.id)

    @classmethod
    def settlement_application(cls, user: User, match: Match) -> SettlementApplication:
        """
        赛事结算申请

        :param user:
        :param match:
        :return SettlementApplication
        """
        # if match.finished:
        #     raise SettlementApplicationException("赛事已结算")

        with cls.database.transaction():
            application = SettlementApplication.select()\
                .where(SettlementApplication.match_id == match.id,
                       SettlementApplication.processing >= ApplicationState
                       .requesting.value)
            if application.exists():
                raise SettlementApplicationExist("结算申请已存在")

            inst = SettlementApplication\
                .create(match_id=match.id, team_id=match.team_id,
                        user_id=user.id)
            return inst

    @classmethod
    def get_preview_qrcode(cls, match_id):
        preview_url = "parteam://matches/{match_id}?preview=1"\
            .format(match_id=match_id)
        return qrcode.make(preview_url)


class MatchStatusService(object):

    @classmethod
    def do_like(cls, user_id: int, match_status: MatchStatus) \
            -> MatchStatus:
        """
        点赞
        :param user_id:
        :param match_status:
        :return:
        """
        return match_status.do_like(user_id=user_id)

    @classmethod
    def undo_like(cls, user_id: int, match_status: MatchStatus)\
            -> MatchStatus:
        """
        取消点赞
        :param user_id:
        :param match_status:
        :return:
        """
        return match_status.undo_like(user_id=user_id)

    @classmethod
    def get_likes(cls, match_status: MatchStatus) -> SelectQuery:
        """
        获取点赞用户列表
        :param match_status:
        :return:
        """
        return match_status.get_likes()


class SettlementService(BaseService):

    @classmethod
    def approve(cls, application: SettlementApplication, admin: Admin):
        """
        批准申请
        :param application:
        :param admin: 审核人
        """
        from yiyun.tasks.match import settlement
        if application.processing != ApplicationState.requesting.value:
            raise ApplicationProcessingException("只能批准 `待审核` 的结算申请")

        SettlementApplication\
            .update(approve_at=datetime.now(), admin_id=admin.id,
                    processing=ApplicationState.approved.value)\
            .where(SettlementApplication.id == application.id).execute()

        settlement.delay(application_id=application.id)

    @classmethod
    def disapprove(cls, application: SettlementApplication, admin: Admin):
        """
        申请驳回
        :param application: 申请
        :param admin: 审核人
        """
        if application.processing != ApplicationState.requesting.value:
            raise ApplicationProcessingException("只能驳回`待审核`的结算申请")

        SettlementApplication\
            .update(processing=ApplicationState.disapproved.value,
                    admin_id=admin.id, approve_at=datetime.now())\
            .where(SettlementApplication.id == application.id).execute()
