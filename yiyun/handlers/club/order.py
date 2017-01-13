from datetime import datetime, timedelta

import geohash
import tornado.escape
import tornado.web
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from wtforms import ValidationError
from yiyun.helpers import is_mobile, intval, decimalval
from yiyun.models import (fn, User, Team, Activity, ActivityMember, MatchMember,
                          ChinaCity, TeamMember, TeamSettings, TeamOrder, TeamCashLog)

from .forms.order import ApplyCashFrom

from yiyun import tasks
from yiyun.libs.parteam import Parteam


@club_app.route("/orders", name="club_orders")
class Orders(ClubBaseHandler):
    """订单列表"""

    def get(self):
        parteam = Parteam(self.settings["parteam_api_url"])

        state = intval(self.get_argument("state", 100))
        start = self.get_argument("start", "")
        end = self.get_argument("end", "")

        orders = TeamOrder.select(
            TeamOrder,
            MatchMember
        ).join(
            MatchMember,
            on=(TeamOrder.id == MatchMember.order_id).alias("match_member")
        ).where(
            TeamOrder.team == self.current_team
        ).order_by(
            TeamOrder.id.desc()
        )

        if start:
            start = "%s 00:00:00" % start
            orders = orders.where(TeamOrder.created >= start)

        if end:
            end = "%s 23:59:59" % end
            orders = orders.where(TeamOrder.created <= end)

        if state != 100:
            orders = orders.where(TeamOrder.state ==
                                  TeamOrder.OrderState(state))

        query = self.paginate_query(orders)
        orders = []
        for item in query:
            orders.append(dict(item.info,
                               order_type_name=item.order_type_name,
                               state_name=item.state_name,
                               payment_method_name=item.payment_method_name,
                               match_member=item.match_member.info))

        user_ids = [order["match_member"]["user_id"] for order in orders
                    if order["match_member"]["user_id"]]

        if user_ids:
            user_infos = parteam.parteam_user(user_ids)
            for order in orders:
                order["user_info"] =\
                    user_infos.get(order["match_member"]["user_id"])

        self.render("orders/orders.html",
                    states=TeamOrder.ORDER_STATES,
                    orders=orders,
                    pagination=query.pagination
                    )


@club_app.route(r"/activities/refunded_orders",
                name="club_activities_refunded_orders")
class ActivityRefundedOrders(ClubBaseHandler):
    """ 活动退款订单

    """

    def get(self):
        orders = ActivityMember.select(
            ActivityMember,
            TeamOrder,
            User
        ).join(
            TeamOrder, on=(TeamOrder.id == ActivityMember.order_id).alias("order")
        ).switch(
            ActivityMember
        ).join(
            User, on=(ActivityMember.user == User.id).alias("user")
        ).where(
            TeamOrder.team == self.current_team,
            TeamOrder.refund_state > TeamOrder.OrderRefundState.NO_REFUND
        ).order_by(
            TeamOrder.refunded_time.desc()
        )

        orders = self.paginate_query(orders)

        self.render("activity/refunded_orders.html",
                    orders=orders
                    )


@club_app.route(r"/cash_log", name="club_cash_logs")
class TeamCashLogsHandler(ClubBaseHandler):
    """ 提现记录
    """

    def get(self):

        state = intval(self.get_argument("state", 100))
        start = self.get_argument("start", "")
        end = self.get_argument("end", "")

        query = TeamCashLog.select().where(
            TeamCashLog.team_id == self.current_team.id
        ).order_by(
            TeamCashLog.created.desc()
        )

        if start:
            query = query.where(TeamCashLog.created >= start)

        if end:
            query = query.where(TeamCashLog.created <= end)

        if state != 100:
            query = query.where(TeamCashLog.state == TeamCashLog.TeamCashState(state))

        cash_logs = self.paginate_query(query)

        self.render("orders/cash_logs.html",
                    cash_logs=cash_logs,
                    states=TeamCashLog.STATE_NAMES
                    )


@club_app.route(r"/apply-cash", name="club_apply_cash")
class ApplyCashHandler(ClubBaseHandler):
    """ 申请提现

    """

    def get(self):

        form = ApplyCashFrom()

        settings = TeamSettings.get_or_none(team=self.current_team.id)

        self.render("orders/apply_cash.html",
                    form=form,
                    settings=settings
                    )

    def validate_amount(self, form):
        cash_amount = decimalval(self.get_argument("amount"))

        if cash_amount > self.current_team.credit:
            form.amount.errors = [ValidationError("超过可提现金额")]
            return False

        return True

    def post(self):

        form = ApplyCashFrom(self.arguments)
        settings = TeamSettings.get_or_none(team=self.current_team.id)

        if form.validate() and self.validate_amount(form) and \
                settings and settings.cash_ready():
            with(self.db.transaction()):
                team = Team.select().where(
                    Team.id == self.current_team.id
                ).for_update().get()

                cash_amount = decimalval(self.get_argument("amount"))

                TeamCashLog.create(
                    team_id=team.id,
                    amount=cash_amount,
                    cash_account_type=settings.cash_type,
                    cash_account=settings.cash_account,
                    cash_name=settings.cash_username,
                    order_no=TeamCashLog.get_new_order_no()
                )

                # 将收入打到俱乐部账上
                Team.update(
                    credit=Team.credit - cash_amount,
                    cashed_amount=Team.cashed_amount + cash_amount,
                    updated=datetime.now()
                ).where(
                    Team.id == team.id
                ).execute()

            self.redirect(self.reverse_url("club_cash_logs"))
            return

        self.render("orders/apply_cash.html",
                    form=form,
                    settings=settings
                    )
