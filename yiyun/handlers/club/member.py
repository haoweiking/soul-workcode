import peewee

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import HttpForbiddenError, HttpBadRequestError, Http404
from yiyun.models import (Team, TeamMember, TeamMemberGroup, TeamMemberAccountLog, User,
                          Activity, ActivityMember, TeamOrder)
from yiyun.helpers import intval, floatval
from yiyun.libs.parteam import Parteam


class MemberHandlerHelper(object):
    pass


@club_app.route("/members_list", name="club_members_list")
class MembersList(ClubBaseHandler):

    """
    俱乐部为 赛事举办方 时的会员列表
    """

    _VALID_SORT_TYPE = ("nick_desc", "credit_desc", "credit_asc",)
    _VALID_ROLE = ("member", "vip", "black_list")

    def get(self):
        parteam = Parteam(self.settings["parteam_api_url"])

        team = self.current_team
        groups = TeamMemberGroup.select().where(TeamMemberGroup.team == team)

        query = TeamMember.select(TeamMember).\
            where(TeamMember.team == team)

        # 按备注名字搜索
        kw = self.get_argument("kw", None)
        if kw:
            query = query.where(
                (TeamMember.nick.contains(kw)
                 ) | (User.mobile == kw)
            )

        sort = self.get_argument("sort", "")
        if sort in self._VALID_SORT_TYPE:
            if sort == "-name":
                query = query.order_by(TeamMember.nick.desc())
            elif sort == "-credit":
                query = query.order_by(TeamMember.credit.desc())
            elif sort == "credit":
                query = query.order_by(TeamMember.credit.asc())

        filter_by_role = self.get_argument("role", None)
        if filter_by_role in self._VALID_ROLE:
            if filter_by_role == "member":
                pass
            elif filter_by_role == "vip":
                query = query.where(TeamMember.is_vip == True)
            elif filter_by_role == "black_list":
                pass

        # 分 group 查询
        group_name = self.get_argument("group", None)
        if group_name:
            query = query.where(TeamMember.group_name == group_name)

        members = self.paginate_query(query)

        # user_ids = map(lambda member: member.parteam_user_id, members)
        user_ids = [member.parteam_user_id for member in members
                    if member.parteam_user_id]
        if user_ids:
            user_infos = parteam.parteam_user(user_ids)

            for member in members:
                member.user_info = user_infos.get(member.parteam_user_id)

        self.render("member/parteam_members_list.html",
                    groups=groups,
                    groups_json=[g.info for g in groups],
                    members=members)


@club_app.route("/members", name="club_members")
class Members(ClubBaseHandler):

    _VALID_SORT_TYPE = ("nick_desc", "credit_desc", "credit_asc",)
    _VALID_ROLE = ("member", "vip", "black_list")

    def get(self):
        team = self.current_team
        groups = TeamMemberGroup.select().where(TeamMemberGroup.team == team)

        query = TeamMember.select(
            TeamMember,
            User
        ).join(
            User, on=(User.id == TeamMember.user).alias("user")
        ).where(
            TeamMember.team == team
        )

        # 按备注名字搜索
        kw = self.get_argument("kw", None)
        if kw:
            query = query.where(
                (TeamMember.nick.contains(kw)
                 ) | (User.mobile == kw)
            )

        sort = self.get_argument("sort", "")
        if sort in self._VALID_SORT_TYPE:
            if sort == "-name":
                query = query.order_by(TeamMember.nick.desc())
            elif sort == "-credit":
                query = query.order_by(TeamMember.credit.desc())
            elif sort == "credit":
                query = query.order_by(TeamMember.credit.asc())

        filter_by_role = self.get_argument("role", None)
        if filter_by_role in self._VALID_ROLE:
            if filter_by_role == "member":
                pass
            elif filter_by_role == "vip":
                query = query.where(TeamMember.is_vip == True)
            elif filter_by_role == "black_list":
                pass

        # 分 group 查询
        group_name = self.get_argument('group', None)
        if group_name:
            query = query.where(TeamMember.group_name == group_name)

        members = self.paginate_query(query)

        self.render("member/list.html",
                    groups=groups,
                    groups_json=[g.info for g in groups],
                    members=members
                    )

    def post(self):

        action = self.get_argument("action")
        user_id = self.get_argument("user_id")

        if action == "change_group":
            group_name = self.get_argument("group_name")

            member = Team.get_member(self.current_team.id, user_id)

            TeamMember.update(
                group_name=group_name
            ).where(
                TeamMember.team == self.current_team,
                TeamMember.user == user_id
            ).execute()

            # 计算新分组成员数量
            TeamMemberGroup.update_members_count(
                self.current_team.id, group_name)

            # 计算旧分组成员数量
            TeamMemberGroup.update_members_count(
                self.current_team.id, member.group_name)

        elif action == "apply":
            user = User.get_or_404(id=user_id)
            self.current_team.apply(user)

        elif action == "remove_member":
            member = Team.get_member(self.current_team.id, user_id)
            if member:
                if not member.can_leave():
                    raise HttpForbiddenError("该会员有财务没有结清，不能踢出")

                user = User.get_or_404(id=user_id)
                self.current_team.leave(user)

                TeamMemberGroup.update_members_count(
                    self.current_team.id, member.group_name)

        elif action == "recharge":

            amount = intval(self.get_argument("amount"))
            freetimes = intval(self.get_argument("freetimes"))
            remark = self.get_argument("remark")

            member = Team.get_member(self.current_team.id, user_id)
            if member:
                TeamMember.change_credit(self.current_team.id,
                                         user_id=user_id,
                                         change_type=1,  # 充值类型为后台操作
                                         change_amount=amount,
                                         free_times=freetimes,
                                         operator_id=self.current_user.id,
                                         note=remark)

        elif action == "deduction":

            amount = intval(self.get_argument("amount"))
            freetimes = intval(self.get_argument("freetimes"))
            remark = self.get_argument("remark")

            member = Team.get_member(self.current_team.id, user_id)
            if member:
                TeamMember.change_credit(self.current_team.id,
                                         user_id=user_id,
                                         change_type=1,  # 充值类型为后台操作
                                         change_amount=0 - amount,
                                         free_times=0 - freetimes,
                                         operator_id=self.current_user.id,
                                         note=remark)

        self.write_success()


@club_app.route(r"/members/add/multiple", name="club_members_add_multiple")
class MemberAddMultiple(ClubBaseHandler):

    def get(self):
        pass

    def post(self):
        pass


@club_app.route(r"/members/([\d]+)", name="club_member_detail")
class DetailHandler(ClubBaseHandler):

    def get(self, user_id):
        try:
            user = User.select(
                User,
                TeamMember
            ).join(
                TeamMember, on=(TeamMember.user == User.id).alias("member")
            ).where(
                TeamMember.team == self.current_team,
                TeamMember.user == user_id
            ).get()
        except User.DoesNotExist:
            raise Http404()

        self.render("member/detail.html",
                    user=user,
                    groups=self.current_team.groups)

    def post(self):
        pass


@club_app.route(r"/members/([\d]+)/activities", name="club_members_activities")
class MembersActivities(ClubBaseHandler):

    def get(self, user_id):

        query = Activity.select(
            Activity,
            ActivityMember,
            TeamOrder,
        ).join(
            ActivityMember,
            on=(ActivityMember.activity == Activity.id).alias('member')
        ).switch(
            Activity
        ).join(
            TeamOrder,
            join_type=peewee.JOIN_LEFT_OUTER,
            on=(ActivityMember.order_id == TeamOrder.id).alias('order')
        ).where(
            Activity.team == self.current_team,
            ActivityMember.user == user_id
        ).order_by(
            ActivityMember.id.desc()
        )

        query = self.paginate_query(query, per_page=20)

        activities = []
        for activity in query:
            activity_info = activity.get_info()
            activity_info['member'] = activity.member.get_info()
            activity_info['order'] = activity.order.list_info
            activity_info['order']['state_name'] = activity.order.state_name
            activities.append(activity_info)

        self.write({
            "activities": activities,
            "pagination": query.pagination.info
        })


@club_app.route(r"/members/([\d]+)/account_logs", name="club_members_account_logs")
class MembersAccountLogs(ClubBaseHandler):

    def get(self, user_id):

        query = TeamMemberAccountLog.select().where(
            TeamMemberAccountLog.team == self.current_team,
            TeamMemberAccountLog.user == user_id
        )

        query = self.paginate_query(query, per_page=20)

        logs = []
        for log in query:
            log_info = log.info
            log_info['change_type_name'] = log.change_type_name
            logs.append(log_info)

        self.write({
            "account_logs": logs,
            "pagination": query.pagination.info
        })


@club_app.route(r"/members/([\d]+)/orders", name="club_members_orders")
class MembersOrders(ClubBaseHandler):

    def get(self, user_id):

        query = TeamOrder.select().where(
            TeamOrder.team == self.current_team,
            TeamOrder.user == user_id
        )

        query = self.paginate_query(query, per_page=20)

        orders = []
        for order in query:
            orders_info = order.info
            orders_info['state_name'] = order.state_name
            orders_info['refund_state_name'] = order.refund_state_name
            orders_info['payment_method_name'] = order.payment_method_name
            orders_info['order_type_name'] = order.order_type_name
            orders.append(orders_info)

        self.write({
            "orders": orders,
            "pagination": query.pagination.info
        })


@club_app.route(r"/member_groups", name="club_member_groups")
class MemberGroups(ClubBaseHandler):

    def get(self):
        groups = self.current_team.groups
        self.render("member/groups.html", groups=groups)

    def post(self):
        group_id = int(self.get_argument("group_id"))
        group_name = self.get_argument("group_name")

        query = TeamMemberGroup.select().where(
            TeamMemberGroup.team == self.current_team,
            TeamMemberGroup.name == group_name
        )

        if group_id > 0:
            query = query.where(TeamMemberGroup.id != group_id)

        if query.exists():
            raise HttpBadRequestError("分组名称已存在")

        if group_id == 0:
            try:
                group = TeamMemberGroup.create(
                    team=self.current_team,
                    name=group_name
                )
            except peewee.IntegrityError:
                raise HttpForbiddenError("该分组已经存在")

        else:
            TeamMemberGroup.update(
                name=group_name
            ).where(
                TeamMemberGroup.id == group_id,
                TeamMemberGroup.team == self.current_team
            ).execute()

            group = TeamMemberGroup.get_or_404(id=group_id)

        self.write({
            "group": group.info
        })

    def delete(self):

        group_id = self.get_argument("group_id")
        group = TeamMemberGroup.get_or_404(id=group_id)

        if group.team != self.current_team:
            raise HttpForbiddenError()

        if TeamMember.select().where(
            TeamMember.team == self.current_team,
            TeamMember.group_name == group.name
        ).count() > 0:
            raise HttpForbiddenError("此分组有会员，不能删除")

        group.delete_instance()

        self.write_success()
