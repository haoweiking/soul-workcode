import logging
import random
import time
from datetime import datetime
from decimal import Decimal
from enum import IntEnum

from cached_property import cached_property
from peewee import (fn, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    DecimalField, DoubleField, IntegrityError)

from yiyun.consts import PaymentMethod
from yiyun.core import current_app as app
from yiyun.ext.database import (JSONTextField, PointField)
from yiyun.models import User, Sport, ListField
from .base import BaseModel


class Team(BaseModel):

    class Meta:
        db_table = 'team'
        order_by = ('-id', )

        indexes = (
            (('lat', 'lng'), False),
        )

    class TeamRole(IntEnum):
        member = 5
        leader = 25
        admin = 50
        super = 100

    STATE_NAMES = {
        0: "待审核",
        1: "正常",
        2: "已关闭",
        3: "审核拒绝"
    }

    name = CharField(max_length=120, index=True, verbose_name="名称")
    description = TextField(default="", verbose_name="介绍")
    notice = TextField(default="", verbose_name="公告")

    sport = ListField(default="", verbose_name="运动类型")
    icon_key = CharField(default="", max_length=120, verbose_name="微标")

    type = IntegerField(default=0, help_text="0 俱乐部 1 赛事主办方")

    country = CharField(default="中国", max_length=128, index=True)
    province = CharField(default="", max_length=128, index=True)
    city = CharField(default="", max_length=128, index=True)

    address = CharField(default="", max_length=250, verbose_name="详细地址")

    contact_person = CharField(default="", max_length=250, verbose_name="联系人")
    contact_phone = CharField(default="", max_length=250, verbose_name="联系电话")

    lat = DoubleField(default=0)
    lng = DoubleField(default=0)
    location = PointField(null=True)

    geohash = CharField(default="", index=True, max_length=16)

    verified = BooleanField(default=False, index=True, verbose_name="是否通过了实名认证")
    verified_reason = TextField(default="", verbose_name="实名认证拒绝原因")

    members_count = IntegerField(default=0, verbose_name="成员数")
    activities_count = IntegerField(default=0, verbose_name="活动数")

    open_type = IntegerField(default=0,
                             index=True,
                             verbose_name="开放类型",
                             choices=[("0", "允许任何人加入"),
                                      ("1", "需要验证"),
                                      # ("2", "交会费加入"),
                                      ("3", "不允许任何人加入")]
                             )

    wx_appid = CharField(default="", max_length=32)

    credit = DecimalField(default=Decimal(
        0), decimal_places=2, verbose_name="余额")
    total_receipts = DecimalField(default=Decimal(
        0), decimal_places=2, verbose_name="总收入")
    cashed_amount = DecimalField(default=Decimal(
        0), decimal_places=2, verbose_name="已提现")

    owner_id = IntegerField(verbose_name="俱乐部主")
    score = IntegerField(default=0, verbose_name="得分")
    state = IntegerField(default=0, index=True, verbose_name="状态")

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    followers_count = IntegerField(default=0, help_text="关注俱乐部的用户数")

    def __str__(self):
        return "Team: %s" % self.id

    def display_sport_type(self):
        sport_names = [name for name in self.sport]
        return ','.join(sport_names)

    @property
    def state_name(self):
        return self.STATE_NAMES.get(self.state, "未知")

    @cached_property
    def info(self):
        info = self.to_dict(exclude=[Team.icon_key])
        info['icon'] = Team.get_cover_urls(self.icon_key)
        return info

    @cached_property
    def mini_info(self):
        info = self.to_dict(only=[Team.id, Team.name,
                                  Team.verified, Team.city])
        info['icon'] = Team.get_cover_urls(self.icon_key)
        return info

    @property
    def icon(self):
        cover_url = app.settings['avatar_url'].rstrip('/')
        return Team.get_cover_urls(self.icon_key, cover_url=cover_url)

    @property
    def icon_url(self):
        icon_info = self.icon
        url = icon_info.get("url", "")
        sizes = icon_info.get("sizes", "")
        if sizes and url:
            sizes = sizes[0]
        else:
            sizes = ""

        return "%s%s" % (url, sizes)

    def get_settings(self):
        settings = TeamSettings.get_or_none(team=self)
        if settings is None:
            settings = TeamSettings()
            settings.team = self

        return settings

    def get_mini_url(self):
        return "%s/c/%s" % (app.settings['club_url'], self.id)

    @classmethod
    def update_activities_count(cls, team_id):
        Team.update(
            activities_count=cls.get_activities_count(team_id)
        ).where(
            Team.id == team_id
        ).execute()

    @classmethod
    def get_activities_count(cls, team_id):
        from .activities import Activity
        return Activity.select().where(Activity.team == team_id).count()

    def add_member(self, user_id, nick="", inviter=None,
                   state=0, role=5):

        if TeamMember.select().where(
            TeamMember.user == user_id,
            TeamMember.team == self
        ).exists():
            return False

        TeamMember.create(
            parteam_user_id=user_id,
            user=None,
            team=self,
            created=datetime.now(),
            joined=datetime.now(),
            inviter=inviter,
            state=state,
            role=role,
            nick=nick
        )

        Team.update(
            members_count=Team.get_members_count(self.id)
        ).where(
            Team.id == self.id
        ).execute()

        return True

    def reject(self, user_id):
        TeamMember.delete().where(
            (TeamMember.team == self
             ) & (TeamMember.user == user_id)
        ).execute()

    def apply(self, user):
        with(self._meta.database.transaction()):
            TeamMember.update(
                state=TeamMember.TeamMemberState.normal,
                role=self.TeamRole.member,
                joined=datetime.now()
            ).where(
                (TeamMember.user == user.id
                 ) & (TeamMember.team == self)
            ).execute()

            Team.update(
                members_count=Team.get_members_count(self.id)
            ).where(
                Team.id == self.id
            ).execute()

    def leave(self, user):
        """ 退出俱乐部

            创建人不能离开, 有账户未结算不能退出,
            可以找俱乐部管理员结清账务后再退出

            Args:
                user: 用户对象

        """

        # 创建人不能离开
        if self.is_superadmin(user.id):
            return False

        member = Team.get_member(self.id, user.id)
        if member is None:
            return False

        if not member.can_leave():
            return False

        with(self._meta.database.transaction()):
            TeamMember.delete().where(
                (TeamMember.team == self
                 ) & (TeamMember.user == user.id)
            ).execute()

            Team.update(
                members_count=Team.get_members_count(self.id)
            ).where(
                Team.id == self.id
            ).execute()

    def get_members(self, limit=20, offset=0, role="", state=None):
        """ 获取俱乐部成员
        """

        q = User.select(
            User, TeamMember
        ).join(
            TeamMember, on=TeamMember.user
        ).where(
            TeamMember.team == self
        )

        if role == "leader":
            q = q.where(TeamMember.role >= self.TeamRole.leader)

        elif role == "admin":
            q = q.where(TeamMember.role >= self.TeamRole.admin)

        if isinstance(state, int):
            q = q.where(TeamMember.state >= state)

        q = q.order_by(
            TeamMember.role.desc()
        ).offset(offset).limit(limit)

        users = []
        for user in q:
            users.append(user)

        return users

    @classmethod
    def get_members_count(cls, team_id):
        return TeamMember.select().where(
            (TeamMember.team == team_id
             ) & (TeamMember.state == TeamMember.TeamMemberState.normal)
        ).count()

    def is_superadmin(self, user_id):
        """ 是否为超级管理员
            俱乐部创建人为超级管理员
        """

        if self.owner_id == user_id:
            return True

        return False

    def is_admin(self, user_id):
        """ 是否为管理员
            管理员由创建人指定
        """
        if self.owner_id == user_id:
            return True

        return Team.get_member_role(self.id, user_id) >= self.TeamRole.admin

    def is_member(self, user_id):
        """ 是否为成员 """

        if self.owner_id == user_id:
            return True

        return Team.get_member_role(self.id, user_id) >= self.TeamRole.member

    def is_pending_member(self, user_id):
        member = Team.get_member(self.id, user_id)
        return member.state == TeamMember.TeamMemberState.pending

    @classmethod
    def get_member_role(cls, team_id, user_id):
        """ 获取成员的角色

            如果成员状态为非正式状态即不是成员
        """

        member = cls.get_member(team_id, user_id)
        if member and member.state == TeamMember.TeamMemberState.pending:
            return member.role

        return 0

    @classmethod
    def get_member(cls, team_id, user_id):
        """ 获取俱乐部成员 """

        try:
            return TeamMember.select().where(
                (TeamMember.team == team_id
                 ) & (TeamMember.user == user_id)
            ).get()

        except TeamMember.DoesNotExist:
            return None

    def add_superadmin(self, user_id):
        """ 添加超管 """

        try:
            TeamMember.create(
                user=user_id,
                team=self,
                role=self.TeamRole.super,
                state=TeamMember.TeamMemberState.normal,
                joined=datetime.now()
            )

        except IntegrityError:
            pass

    def add_admin(self, user_id):
        """ 将成员设置为管理

            必须先添加用户为成员才可以设置为管理员
        """

        with(self.db.transaction()):
            TeamMember.update(
                role=self.TeamRole.admin,
            ).where(
                (TeamMember.user == user_id
                 ) & (TeamMember.team == self)
            ).execute()

    def delete_admin(self, user_id):
        """ 取消成员管理员权限

        """

        with(self.db.transaction()):
            TeamMember.update(
                role=self.TeamRole.member,
            ).where(
                (TeamMember.user == user_id
                 ) & (TeamMember.team == self)
            ).execute()

    def remove(self):
        """删除团队

            不允许删除俱乐部
        """
        pass

    @property
    def groups(self):
        """ 获取俱乐部成员分组列表
        """

        q = TeamMemberGroup.select(
        ).where(
            TeamMemberGroup.team == self
        )

        groups = []
        for group in q:
            groups.append(group)

        return groups

    def get_freetimes_total(self):
        """ 获取全部成员的免费次数之和 """

        return TeamMember.select(
            fn.Sum(TeamMember.free_times).alias("sum")
        ).where(
            TeamMember.team == self.id
        ).scalar() or 0

    def get_credit_total(self, nagitive=False):
        """ 获取全部成员的资金总和
            如果 nagitive = True 则返回全部负资产之和
        """

        sum_q = TeamMember.select(
            fn.Sum(TeamMember.money).alias("sum")
        ).where(
            TeamMember.team == self.id
        )

        if nagitive:
            sum_q = sum_q.where(
                TeamMember.money < 0
            )

        else:
            sum_q = sum_q.where(
                TeamMember.money >= 0
            )

        return sum_q.scalar() or 0

    @property
    def owner(self):
        return User.get_or_none(id=self.owner_id)

    def get_follower(self, user_id: int):
        """
        获取俱乐部关注者
        :param user_id:
        :return:
        """
        follower = TeamFollower.get_or_none(user_id=user_id, team_id=self.id)
        return follower

    def add_follower(self, user_id: int):
        """添加关注者"""
        with Team._meta.database.transaction():
            TeamFollower.create(user_id=user_id, team_id=self.id)
            Team.update(followers_count=Team.followers_count + 1)\
                .where(Team.id == self.id).execute()

    def delete_follower(self, user_id: int):
        """删除专注者"""
        with Team._meta.database.transaction():
            rows = TeamFollower.delete()\
                .where(TeamFollower.user_id == user_id,
                       TeamFollower.team_id == self.id)\
                .execute()
            Team.update(followers_count=Team.followers_count - rows)\
                .where(Team.id == self.id).execute()


class TeamSettings(BaseModel):

    """ 团队设置信息 """

    class Meta:
        db_table = "team_settings"

    CASH_TYPE_NAMES = {
        "alipay": "支付宝"
    }

    team = ForeignKeyField(Team, related_name="team_settings_team")

    default_credit_limit = DecimalField(default=Decimal(0),
                                        decimal_places=2,
                                        verbose_name="默认可透支额度")

    cash_type = CharField(default="", verbose_name="提现方式")
    cash_account = CharField(default="", max_length=256,
                             verbose_name="提现帐号")
    cash_username = CharField(default="", verbose_name="提现帐号对应名字")

    recharge_enabled = BooleanField(default=False, verbose_name="是否允许用户在线充值")

    @property
    def team_id(self):
        return self._data['team']

    @property
    def cash_type_name(self):
        return self.CASH_TYPE_NAMES.get(self.cash_type, "未知")

    def cash_ready(self):

        if self.cash_account and \
                self.cash_type and \
                self.cash_username:
            return True

        return False


class TeamMember(BaseModel):

    """ 团队成员 """

    class Meta:
        db_table = 'team_member'
        order_by = ('-role', '-joined', )

        indexes = (
            (('user', 'team'), True),
        )

    class TeamMemberState(IntEnum):
        blocked = -2
        stranger = -1
        pending = 0
        normal = 1

    MEMBER_STATES = {
        TeamMemberState.stranger: "路人",
        TeamMemberState.pending: "待审核",
        TeamMemberState.normal: "正常",
        TeamMemberState.blocked: "黑名单"
    }

    team = ForeignKeyField(Team, related_name="members")
    user = ForeignKeyField(User, related_name="teams", index=True, null=True)
    parteam_user_id = IntegerField(verbose_name="对应派队系统用户")

    nick = CharField(default="", verbose_name="昵称")

    inviter = ForeignKeyField(User, related_name="team_member_inviters",
                              null=True, verbose_name="邀请人")

    role = IntegerField(default=Team.TeamRole.member, index=True)

    push_enabled = BooleanField(default=True, verbose_name="接受通知")

    credit = DecimalField(default=Decimal(0),
                          decimal_places=2,
                          verbose_name="余额",
                          help_text="可以为负")

    credit_limit = DecimalField(default=Decimal(0),
                                decimal_places=2,
                                verbose_name="信用额度",
                                help_text="最大透支额度")

    free_times = IntegerField(default=0,
                              verbose_name="次卡余额",
                              help_text="次卡每个点要吧参加一人次允许使用次卡的活动"
                              )
    total_recharge = DecimalField(default=Decimal(0),
                                  decimal_places=2,
                                  verbose_name="总充值金额"
                                  )

    # 分组信息
    group_name = CharField(default="未分组", max_length=64, null=False)

    activities_count = IntegerField(default=0, help_text="此成员在本圈子参加活动数")

    is_vip = BooleanField(default=False,
                          verbose_name="VIP",
                          help_text="是否为会员 充值过会费就是会员")

    state = IntegerField(default=0,
                         index=True,
                         verbose_name="状态",
                         help_text="0 非正式 1 正常 2 黑名单"
                         )

    joined = DateTimeField(null=True, verbose_name="加入时间")
    created = DateTimeField(null=True, verbose_name="创建时间")
    last_activity_time = DateTimeField(null=True, verbose_name="最后活动时间")
    last_update_time = IntegerField(
        default=time.time, help_text="成员在此圈子最后活动时间")

    @classmethod
    def change_credit(cls, team_id, user_id, change_type,
                      change_amount, free_times=0, operator_id=0,
                      note=None, activity_id=0):
        """ 修改成员余额

            Args:
                team_id: 俱乐部ID
                user_id: 成员的用户ID
                change_type: 变更原因 0 活动结算 1 后台操作（添加\扣减） 2 平台充值 3 赠送
                change_amount: 变量金额,正数为加负数为减
                free_times: 变更次卡数量,正数为加负数为减
                operator_id: 操作人ID, 0 表示系统操作: 比如用户使用余额支付和退款到余额
                note: 备注变更原因
                activity_id: 对应活动

            Returns:
                Bool
        """

        try:
            member = TeamMember.select().where(
                (TeamMember.team == team_id
                 ) & (TeamMember.user == user_id)
            ).for_update().get()

        except TeamMember.DoesNotExist:
            member = None

        if not member or not member.is_member():
            raise AssertionError("非俱乐部正式成员不能充值")

        # 保留两位小数
        change_amount = round(change_amount, 2)

        TeamMemberAccountLog.create(
            team=team_id,
            user=user_id,
            operator_id=operator_id,
            change_type=change_type,
            credit_change=change_amount,
            free_times=free_times,
            credit_before=member.credit,
            credit_after=member.credit + change_amount,
            note=note[:200] if note else None,
            activity_id=activity_id
        )

        cls.update(
            credit=cls.credit + change_amount,
            free_times=cls.free_times + free_times
        ).where(
            cls.id == member.id
        ).execute()

        return True

    @property
    def user_id(self):
        return self._data['user']

    @property
    def state_name(self):
        return self.MEMBER_STATES.get(self.state, "未知")

    def to_json(self):
        return self.to_dict(exclude=[TeamMember.inviter])

    def is_member(self):
        return self.role >= Team.TeamRole.member and \
            self.state == self.TeamMemberState.normal

    def is_pending(self):
        return self.state == self.TeamMemberState.pending

    def is_normal(self):
        return self.state == self.TeamMemberState.normal

    def can_leave(self):
        """ 账务结算后才允许退出 """

        return self.credit == 0 and self.free_times == 0

    @classmethod
    def set_vip(cls, team_id=None, user_id=None):
        """设置成员成为VIP
        """

        if team_id is not None and user_id is not None:
            TeamMember.update(
                is_vip=True
            ).where(
                TeamMember.team == team_id,
                TeamMember.user == user_id
            ).execute()

    @property
    def info(self):
        return self.get_info()

    def get_info(self):
        info = self.to_dict(exclude=[TeamMember.user, TeamMember.team,
                                     TeamMember.inviter])
        info['user_id'] = self.user_id
        info['team_id'] = self._data['team']
        info['inviter_id'] = self._data.get('inviter', None)

        return info

    @property
    def account_logs(self):
        """
        获取在本俱乐部的金额变更记录
        Returns: peewee.SelectQuery

        """
        return self._account_logs()

    def get_account_logs(self):
        query = TeamMemberAccountLog.select()\
            .where(TeamMemberAccountLog.team == self.team,
                   TeamMemberAccountLog.user == self.user)
        return query


class TeamMemberGroup(BaseModel):
    """ 圈子成员分组 """

    class Meta:
        db_table = "team_member_group"

        indexes = (
            (('team', 'name'), True),
        )

    team = ForeignKeyField(Team, related_name="groups")
    name = CharField(max_length=64, null=False)
    members_count = IntegerField(default=0)

    @property
    def info(self):
        if not hasattr(self, '_info'):
            self._info = self.to_dict(exclude=[TeamMemberGroup.team, ])
            self._info['team_id'] = self._data['team']

        return self._info

    @staticmethod
    def update_members_count(team_id, group_name):
        members_count = TeamMemberGroup.get_members_count(team_id, group_name)

        TeamMemberGroup.update(
            members_count=members_count
        ).where(
            TeamMemberGroup.team == team_id,
            TeamMemberGroup.name == group_name
        ).execute()

        return members_count

    @staticmethod
    def get_members_count(team_id, group_name):
        return TeamMember.select().where(
            TeamMember.team == team_id,
            TeamMember.group_name == group_name
        ).count()


class TeamMemberAccountLog(BaseModel):
    """ 圈子成员资金变更记录 """

    class Meta:
        db_table = "team_member_account_log"
        indexs = (
            (("team", "user", "operator"), False),
        )
        order_by = ('-created', )

    team = ForeignKeyField(Team, related_name="team_member_account_log_team")
    user = ForeignKeyField(User, related_name="team_member_account_log_user")

    # 本次操作的金额 正的数字就是添加 反之就是消费
    credit_change = DecimalField(decimal_places=2, null=False, help_text="")

    # 免费次数变化
    free_times_change = IntegerField(default=0)

    # 变更原因 0 活动结算 1 后台操作（添加\扣减） 2 平台充值 3 赠送
    change_type = IntegerField(null=False)

    # 操作之前的余额
    credit_before = DecimalField(decimal_places=2, null=False)

    # 本次操作之后的余额
    credit_after = DecimalField(decimal_places=2, null=False)
    note = TextField(default="", verbose_name="备注")
    activity_id = IntegerField(default=0, index=True, verbose_name="关联活动")

    created = DateTimeField(default=datetime.now, verbose_name="记录生成时间")
    operator_id = IntegerField(default=0)


class TeamAdminLog(BaseModel):

    """ 圈子管理员操作记录 """

    class Meta:
        db_table = "team_admin_log"

        indexes = (
            (("team", "operator", "to_user"), False),
        )

        order_by = ('-created',)

    team = ForeignKeyField(Team, related_name="team_admin_log_team")
    operator = ForeignKeyField(User, related_name="team_admin_log_operator")
    to_user = ForeignKeyField(User, related_name="team_admin_log_to_user")

    description = CharField(default="", null=False, verbose_name="操作描述")
    from_ip = CharField(default="", max_length=40,
                        null=False, verbose_name="操作IP")
    created = DateTimeField(default=datetime.now)


class TeamOrder(BaseModel):

    class Meta:
        db_table = "team_order"

        indexes = (
            (("team", "user"), False),
        )

    class OrderState(IntEnum):
        WAIT_BUYER_PAY = 0  # 等待买家付款
        WAIT_PAY_RETURN = 5  # 等待支付确认
        TRADE_BUYER_PAID = 10  # 等待卖家发货，即：买家已付款
        WAIT_BUYER_CONFIRM_GOODS = 15  # 等待买家确认收货，即：卖家已发货
        TRADE_BUYER_SIGNED = 20  # 买家已签收
        TRADE_FINISHED = 25  # 交易完成
        TRADE_CLOSED = -5  # 付款以后用户退款成功，交易自动关闭
        TRADE_CLOSED_BY_USER = -10  # 付款以前，卖家或买家主动关闭交易

    class OrderRefundState(IntEnum):
        NO_REFUND = 0  # 无退款
        PARTIAL_REFUNDING = 5  # 部分退款中
        PARTIAL_REFUNDED = 10  # 已部分退款
        PARTIAL_REFUND_FAILED = 15  # 部分退款失败
        FULL_REFUNDING = 25  # 全额退款中
        FULL_REFUNDED = 30  # 已全额退款
        FULL_REFUND_FAILED = 35  # 全额退款失败

    OrderPaymentMethod = PaymentMethod

    PAYMENT_METHODS = {
        OrderPaymentMethod.CREDIT: "余额",
        OrderPaymentMethod.WXPAY: "微信支付",
        OrderPaymentMethod.ALIPAY: "支付宝"
    }

    ONLINE_PAYMENT_METHODS = [
        OrderPaymentMethod.WXPAY.value,
        OrderPaymentMethod.ALIPAY.value
    ]

    REFUND_STATES = {
        OrderRefundState.NO_REFUND: "无退款",
        OrderRefundState.PARTIAL_REFUNDING: "部分退款中",
        OrderRefundState.PARTIAL_REFUNDED: "已部分退款",
        OrderRefundState.PARTIAL_REFUND_FAILED: "部分退款失败",
        OrderRefundState.FULL_REFUNDING: "全额退款中",
        OrderRefundState.FULL_REFUNDED: "已全额退款",
        OrderRefundState.FULL_REFUND_FAILED: "全额退款失败",
    }

    ORDER_STATES = {
        OrderState.TRADE_CLOSED_BY_USER: "已取消",
        OrderState.TRADE_CLOSED: "已关闭",  # 在支付之前交易被关闭:关闭后的订单如果收到网关付款成功订单自动退款
        OrderState.WAIT_BUYER_PAY: "待支付",
        OrderState.WAIT_PAY_RETURN: "待确认",  # 用户完成支付同步返回成功,等待服务器回调确认支付完成
        OrderState.TRADE_BUYER_PAID: "已支付",
        OrderState.TRADE_FINISHED: "完成"
    }

    class OrderType(IntEnum):
        ACTIVITY = 0
        CONSUME = 10
        MATCH = 20

    ORDER_TYPES = {
        OrderType.ACTIVITY: "参加活动",
        OrderType.MATCH: "赛事报名",
        OrderType.CONSUME: "消费",
    }

    order_no = CharField(unique=True, max_length=16)

    team = ForeignKeyField(Team, null=True, related_name="team_orders")
    user = ForeignKeyField(User, null=True, related_name="user_orders")

    order_type = IntegerField(default=OrderType.ACTIVITY,
                              index=True,
                              verbose_name="订单类型",
                              help_text="")

    activity_id = IntegerField(default=0, index=True, verbose_name="活动ID")

    title = CharField(help_text="活动订单:活动名称+场次日期,商品订单:首个商品名称", max_length=250)
    note = TextField(default="")
    body = JSONTextField(default=None, null=True)

    total_fee = DecimalField(decimal_places=2, verbose_name="订单金额")
    credit_fee = DecimalField(decimal_places=2, default=Decimal(0),
                              verbose_name="余额抵扣金额")
    discount_fee = DecimalField(default=Decimal(0),
                                decimal_places=2,
                                verbose_name="优惠金额")

    discount_code = CharField(default="", verbose_name="折扣码", max_length=64)
    discount_reason = CharField(
        default="", verbose_name="折扣原因", max_length=200)

    use_integral = IntegerField(default=0, verbose_name="使用积分数量")
    integral_fee = DecimalField(default=Decimal(0),
                                decimal_places=2,
                                verbose_name="积分抵扣金额")

    payment_fee = DecimalField(
        default=Decimal(0), decimal_places=2, verbose_name="实付金额")

    payment_method = CharField(verbose_name="支付方法")
    payment_data = JSONTextField(null=True, help_text='支付信息,如微信支付的预支付订单信息')

    gateway_trade_no = CharField(null=True, verbose_name="支付平台订单号")
    gateway_account = CharField(null=True, verbose_name="支付平台账号")

    refund_state = IntegerField(
        default=OrderRefundState.NO_REFUND, verbose_name="退款状态")
    refunded_fee = DecimalField(default=Decimal(
        0), decimal_places=2, verbose_name="退款金额")
    refunded_time = DateTimeField(null=True, verbose_name="退款时间")

    state = IntegerField(
        default=OrderState.WAIT_BUYER_PAY, verbose_name="订单状态")

    paid = DateTimeField(null=True, verbose_name="支付完成时间")
    finished = DateTimeField(null=True, verbose_name="完成时间")
    created = DateTimeField(default=datetime.now, verbose_name="下单时间")
    updated = DateTimeField(default=datetime.now, verbose_name="最后更新时间")
    cancelled = DateTimeField(null=True, verbose_name="取消时间")
    cancel_reason = TextField(default="", verbose_name="取消原因")

    @property
    def team_id(self):
        return self._data['team']

    @property
    def user_id(self):
        return self._data['user']

    @property
    def order_type_name(self):
        return self.ORDER_TYPES.get(self.order_type, "未知")

    @property
    def payment_method_name(self):
        if self.payment_method:
            try:
                return self.PAYMENT_METHODS.get(self.OrderPaymentMethod(self.payment_method), "未知")
            except ValueError:
                pass

        return "未知"

    @property
    def state_name(self):
        return self.ORDER_STATES.get(self.state, "未知")

    @property
    def refund_state_name(self):
        return self.REFUND_STATES.get(self.refund_state, "未知")

    @classmethod
    def get_new_order_no(cls):
        """
        生成唯一订单号
        """
        order_no = "%s%s" % (datetime.now().strftime("%Y%m%d%H"),
                             random.randint(100000, 999999)
                             )

        if cls.select().where(
            cls.order_no == order_no
        ).exists():

            return cls.get_new_order_no()

        return order_no

    def is_refund_failed(self):
        return self.refund_state in (self.OrderRefundState.PARTIAL_REFUND_FAILED.value,
                                     self.OrderRefundState.FULL_REFUND_FAILED.value)

    def refund(self, reason="", free_times=0):
        """ 退款处理 """

        if self.OrderState(self.state) != self.OrderState.TRADE_BUYER_PAID:
            return False

        # 退余额
        if self.credit_fee > 0 or free_times > 0:
            TeamMember.change_credit(self.team_id,
                                     user_id=self.user_id,
                                     change_type=0,
                                     change_amount=self.credit_fee,
                                     free_times=free_times,
                                     operator_id=0,
                                     note=reason,
                                     activity_id=self.activity_id
                                     )

        # 如果有第三方支付原路退回
        if self.payment_method in self.ONLINE_PAYMENT_METHODS and \
                self.payment_fee > 0:

            # 修改订单退款状态正在退款
            TeamOrder.update(
                refund_state=self.OrderRefundState.FULL_REFUNDING,
                note=reason
            ).where(
                TeamOrder.id == self.id
            ).execute()

            from yiyun.tasks import billing

            billing.refund.delay(order_no=self.order_no,
                                 refund_fee=float(self.total_fee))

        else:
            logging.error("修改订单退款状态为退款完成")
            # 修改订单退款状态为退款完成
            TeamOrder.update(
                refund_state=self.OrderRefundState.FULL_REFUNDED
            ).where(
                TeamOrder.id == self.id
            ).execute()

    def get_info(self):
        info = self.to_dict(exclude=[TeamOrder.team, TeamOrder.user])
        info['team_id'] = self._data['team']
        info['user_id'] = self._data['user']
        info['refund_state'] = self.OrderRefundState(self.refund_state).name
        info['state'] = self.OrderState(self.state).name
        return info

    @cached_property
    def list_info(self):
        info = self.to_dict(
            exclude=[TeamOrder.team, TeamOrder.user, TeamOrder.payment_data])

        info['team_id'] = self._data['team']
        info['user_id'] = self._data['user']
        info['refund_state'] = self.OrderRefundState(
            self.refund_state).name if self.refund_state else self.OrderRefundState.NO_REFUND.name
        info['state'] = self.OrderState(self.state).name
        return info


class TeamAccountLog(BaseModel):
    """俱乐部账户变化记录

       记录俱乐部账户变化：
       1. 每个活动场次结算一条收入记录
       2. 用户每笔充值一条收入记录(管理员手工充值不记录，只记录在线支付的)
       3. 俱乐部每笔提现一条支出记录
    """

    class Meta:
        db_table = "team_account_log"
        indexs = (
            (("team", "user", "operator"), False),
        )
        order_by = ('-created', )

    team_id = IntegerField()

    # 本次操作的金额 正的数字就是添加 反之就是消费
    credit_change = DecimalField(decimal_places=2, null=False, help_text="")

    # 变更原因 0 活动结算 1 用户充值 2 提现
    change_type = IntegerField(null=False)

    # 操作之前的余额
    credit_before = DecimalField(decimal_places=2, null=False)

    # 本次操作之后的余额
    credit_after = DecimalField(decimal_places=2, null=False)

    note = TextField(default="", verbose_name="备注")

    activity_id = IntegerField(default=0, index=True, verbose_name="关联活动")

    created = DateTimeField(default=datetime.now, verbose_name="记录生成时间")
    operator_id = IntegerField(default=0)

    @property
    def change_type_name(self):
        if self.change_type == 0:
            return "参加活动"

        elif self.change_type == 1:
            return "充值"

        elif self.change_type == 2:
            return "提现"

        return "未知"


class TeamCashLog(BaseModel):
    """ 提现记录

    """

    class Meta:
        db_table = "team_cash_log"

        indexes = (
            (("team_id", "operator_id", ), False),
        )

    class TeamCashState(IntEnum):
        WAIT_PAY = 0  # 等待处理
        WAIT_RETURN = 5
        PAID = 10  # 已处理
        FAILED = 20  # 提现失败

    STATE_NAMES = {
        TeamCashState.WAIT_PAY: "等待处理",
        TeamCashState.WAIT_RETURN: "正在处理",
        TeamCashState.PAID: "提现成功",
        TeamCashState.FAILED: "提现失败"
    }

    team_id = IntegerField(index=True)
    operator_id = IntegerField(index=True, default=0)

    amount = DecimalField(default=Decimal(
        0), decimal_places=2, verbose_name="提现金额")

    cash_account_type = CharField(default="alipay", verbose_name="提现账号类型")
    cash_account = CharField(null=True, verbose_name="提现账号")
    cash_name = CharField(null=True, verbose_name="提现账号名")

    order_no = CharField(unique=True, max_length=16)
    trade_no = CharField(default="", null=True)

    created = DateTimeField(default=datetime.now)
    paid = DateTimeField(null=True)
    confirmed = DateTimeField(null=True)  # 确认时间

    state = IntegerField(default=TeamCashState.WAIT_PAY)

    @property
    def state_name(self):
        return self.STATE_NAMES.get(self.TeamCashState(self.state), "未知")

    @classmethod
    def get_new_order_no(cls):
        order_no = "C%s%s" % (datetime.now().strftime("%Y%m%d%H"),
                              random.randint(10000, 99999))

        if cls.select().where(
            cls.order_no == order_no
        ).exists():

            return cls.get_new_order_no()

        return order_no


class TeamOAuthUser(BaseModel):

    WEIBO = 'weibo'
    WEIXIN = 'weixin'
    QQ = 'qq'

    SERVICE_CHOICE = (
        (WEIBO, '微博'),
        (WEIXIN, '微信'),
        (QQ, 'QQ')
    )

    class Meta:
        db_table = 'team_member_oauth_user'

    team = ForeignKeyField(Team)
    member = ForeignKeyField(TeamMember)
    user = ForeignKeyField(User, related_name='auth_user', null=True,
                           default=None)
    service = CharField(verbose_name='服务', choices=SERVICE_CHOICE)

    openid = CharField(help_text='用户唯一标识')
    access_token = CharField(help_text='access token')
    expires_in = IntegerField(help_text='过期时间')
    refresh_token = CharField(help_text='用户刷新 access token')
    user_info = JSONTextField(null=True)


class TeamFollower(BaseModel):
    """俱乐部/ ParteamUser 关注 M2M"""

    team_id = IntegerField(help_text="俱乐部 Team.id")
    user_id = IntegerField(help_text="关注俱乐部的 ParteamUser ID")
    created = DateTimeField(help_text="关注时间", default=datetime.now)

    @cached_property
    def info(self):
        info = self.to_dict(exclude=[])
        return info


class TeamCertifyApplication(BaseModel):

    """
    主办方实名认证申请记录
    """

    class ApplicationState(IntEnum):
        disapproved = -1
        requesting = 1
        approved = 2

    APPLICATION_STATES = {
        ApplicationState.approved: "已批准",
        ApplicationState.disapproved: "已驳回",
        ApplicationState.requesting: "已请求"
    }

    class Meta:
        db_table = "team_certify_application"

    team_id = IntegerField(verbose_name="主办方")
    enterprise_name = CharField(verbose_name="企业名称",
                                help_text="填写营业执照上公司全称，个体工商户填写字号名称")
    license_number = CharField(verbose_name="营业执照注册号",
                               help_text="填写营业执照上的营业执照注册号或统一社会信用代码")
    license_img_key = CharField(verbose_name="营业执照扫描件",
                                help_text="营业执照正副本均可，文字/盖章需清晰可见")

    director = CharField(verbose_name="法定代表人姓名",
                         help_text="填写营业执照上的法定代表人姓名，个体工商户填写经营者姓名")
    director_id = CharField(verbose_name="法定代表人身份证号",
                            help_text="填写与法定代表人姓名对应的18位二代身份证号")
    director_id_card_front_side_img_key =\
        CharField(verbose_name="法定代表人身份证正面")
    director_id_card_back_side_img_key =\
        CharField(verbose_name="法定代表人身份证反面")

    contact_name = CharField(verbose_name="企业联系人",
                             help_text="填写联系人姓名")
    contact_phone = CharField(verbose_name="企业联系人手机号")

    created = DateTimeField(verbose_name="申请时间", default=datetime.now)
    updated = DateTimeField(verbose_name="修改时间", default=datetime.now)
    state = IntegerField(help_text="申请状态",
                         default=ApplicationState.requesting.value)

    @property
    def license_img_url(self):
        return self.get_attach_url(self.license_img_key).get("url")

    @property
    def director_id_card_front_side_img_url(self):
        return self.get_attach_url(self.director_id_card_front_side_img_key).\
            get("url")

    @property
    def director_id_card_back_side_img_url(self):
        return self.get_attach_url(self.director_id_card_back_side_img_key).\
            get("url")

    @property
    def is_requesting(self):
        return self.state == self.ApplicationState.requesting

    @property
    def is_approved(self):
        return self.state == self.ApplicationState.approved

    @property
    def is_disapproved(self):
        return self.state == self.ApplicationState.disapproved

    def set_approved(self):
        self.state = self.ApplicationState.approved

    def set_disapproved(self):
        self.state = self.ApplicationState.disapproved

    def set_requesting(self):
        self.state = self.ApplicationState.requesting
