import logging
import hashlib
import time
from datetime import datetime

from peewee import JOIN

from yiyun.models import (Team, TeamMember, TeamOrder, TeamCashLog,
                          User, Activity)

from yiyun.helpers import intval
from .base import AdminBaseHandler, admin_app


@admin_app.route(r'/orders', name="admin_orders")
class OrderHandler(AdminBaseHandler):

    def get(self):
        """订单列表"""

        state = intval(self.get_argument("state", 100))
        start = self.get_argument("start", "")
        end = self.get_argument("end", "")

        query = TeamOrder.select(
            TeamOrder,
            Team,
            Activity,
        ).join(
            Team, on=(Team.id == TeamOrder.team).alias("team")
        ).switch(
            TeamOrder
        ).join(
            Activity,
            join_type=JOIN.LEFT_OUTER,
            on=(Activity.id == TeamOrder.activity_id).alias("activity")
        )

        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.join(
                User,
                on=(User.id == Team.owner_id)
            ).where(
                User.province << self.current_user.valid_manage_provinces
            )

        kw = self.get_argument("kw", "")
        if kw:
            query = query.where(TeamOrder.title ** ("%%%s%%" % kw))

        if start:
            start = "%s 00:00:00" % start
            query = query.where(TeamOrder.created >= start)

        if end:
            end = "%s 23:59:59" % end
            query = query.where(TeamOrder.created <= end)

        if state != 100:
            query = query.where(TeamOrder.state == TeamOrder.OrderState(state))

        query = query.order_by(TeamOrder.id.desc())
        orders = self.paginate_query(query)

        self.render("order/orders.html",
                    states=TeamOrder.ORDER_STATES,
                    orders=orders,
                    )

    def post(self):
        action = self.get_argument("action")

        if action == "refund":
            order_id = self.get_argument("order_id")
            order = TeamOrder.get_or_404(id=order_id)
            if order.is_refund_failed():
                order.refund()

        self.write_success()


@admin_app.route(r'/cash-applies', name="admin_cash_applies")
class CashAppliesHandler(AdminBaseHandler):

    def get(self):
        """提现申请"""

        team_id = intval(self.get_argument("team_id", 0))
        keyword = self.get_argument("kw", "")
        state = intval(self.get_argument("state", 0))
        sort = intval(self.get_argument("sort", 0))

        query = TeamCashLog.select(
            TeamCashLog,
            Team
        ).join(
            Team, on=(Team.id == TeamCashLog.team_id).alias("team")
        )

        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.where(Team.province <<
                                self.current_user.valid_manage_provinces)

        if state >= 0:
            query = query.where(TeamCashLog.state == state)

        if keyword:
            query = query.where(Team.name.contains(keyword))

        if team_id > 0:
            query = query.where(Team.team_id == team_id)

        if state == 0:
            query = query.order_by(TeamCashLog.id.asc())
        else:
            query = query.order_by(TeamCashLog.id.desc())

        cash_logs = self.paginate_query(query)

        self.render("order/cash_logs.html",
                    cash_logs=cash_logs,
                    )

    def post(self):

        action = self.get_argument("action")
        logid = self.get_argument("logid")

        if action == "finish":
            TeamCashLog.update(
                state=TeamCashLog.TeamCashState.PAID,
                paid=datetime.now()
            ).where(
                TeamCashLog.id == logid,
                TeamCashLog.state != TeamCashLog.TeamCashState.PAID
            ).execute()

        self.write_success()
