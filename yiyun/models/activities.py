from datetime import datetime, timedelta
from decimal import Decimal
from enum import IntEnum
import geohash

from .base import BaseModel

from cached_property import cached_property
from peewee import (fn, BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured,
                    CompositeKey, IntegrityError)

from yiyun.ext.database import (GeoHashField, JSONTextField, ChoiceField,
                                ListField, PointField)

from yiyun.models import User, Team, TeamMemberGroup, TeamOrder, ChinaCity, Sport


class Activity(BaseModel):

    class PaymentType(IntEnum):
        ONLINE_PAY = 0
        CASH_PAY = 1

    # 活动状态可选值
    class ActivityState(IntEnum):
        closed = -1
        cancelled = 0
        opening = 1
        finished = 2

    STATES = {
        ActivityState.closed: "已关闭",
        ActivityState.cancelled: "已取消",
        ActivityState.opening: "进行中",
        ActivityState.finished: "已结束"
    }

    team = ForeignKeyField(Team, related_name="team_activities",
                           verbose_name="所属俱乐部")
    creator = ForeignKeyField(User, related_name="user_created_activities",
                              verbose_name="创建人")

    title = CharField(max_length=180, null=False,
                      index=True, verbose_name="标题")

    type = IntegerField(default=0, verbose_name="活动类型",
                        choices=((0, "活动"), (1, "比赛")))

    sport = ForeignKeyField(Sport, null=True, verbose_name="运动类型")

    leader = ForeignKeyField(User, null=True,
                             related_name="user_leader_activities",
                             verbose_name="组织者")

    contact_person = CharField(default="", max_length=250, verbose_name="联系人")
    contact_phone = CharField(default="", max_length=250, verbose_name="联系电话")

    description = TextField(null=False, verbose_name="描述")

    country = CharField(default="中国", max_length=128)
    province = CharField(default="",
                         max_length=128,
                         choices=ChinaCity.get_provinces(),
                         verbose_name="省份")

    city = CharField(default="",
                     max_length=128,
                     index=True,
                     verbose_name="城市",
                     choices=[])

    address = CharField(default="", max_length=250, verbose_name="活动地址")

    # 活动当前坐标,通过地址获取
    lat = DoubleField(default=0)
    lng = DoubleField(default=0)
    location = PointField(null=True)
    geohash = CharField(default="", index=True, max_length=16)

    gym_id = IntegerField(default=0, verbose_name="场馆ID")

    min_members = IntegerField(default=0)
    max_members = IntegerField(default=0, verbose_name="人数限制")
    public_memebers = BooleanField(default=True, verbose_name="公开报名人列表")

    members_count = IntegerField(default=0)
    comments_count = IntegerField(default=0)

    recommend_time = IntegerField(default=0, verbose_name="推荐时间")
    recommend_region = IntegerField(default=0, verbose_name="推荐范围",
                                    help_text=" # 0 全国 1 同城")

    payment_type = IntegerField(default=0,
                                verbose_name="支付方式",
                                help_text="0 在线支付 1 线下支付, 不允许修改")

    allow_free_times = BooleanField(default=False,
                                    verbose_name="允许使用次卡")

    # 活动针对的组别列表 默认为空 代表针对全部用户
    allow_groups = ListField(default="", null=True,
                             verbose_name="分组限制",
                             choices=[]
                             )

    allow_agents = IntegerField(default=0, verbose_name="允许代报人数")

    start_time = DateTimeField(null=True, verbose_name="开始时间")
    end_time = DateTimeField(null=True, verbose_name="结束时间")
    duration = IntegerField(default=0,
                            verbose_name="活动持续时间",
                            help_text="自动根据开始和结束时间计算")

    repeat_type = CharField(default="", verbose_name="重复类型")
    repeat_end = DateTimeField(null=True, verbose_name="结束重复")

    month_day = IntegerField(default=0, help_text="每月几日循环")
    week_day = IntegerField(default=0, help_text="每周几循环")

    join_start = DateTimeField(null=True, verbose_name="报名开始时间")
    join_end = DateTimeField(null=True, verbose_name="报名截止时间")

    cancelled = DateTimeField(null=True, verbose_name="取消时间")
    cancel_reason = TextField(default="", verbose_name="取消原因")

    verified = BooleanField(default=False, index=True)
    verify_reason = CharField(default="", max_length=250)

    price = DecimalField(
        default=Decimal(0), decimal_places=2, verbose_name="价格")
    female_price = DecimalField(
        default=Decimal(0), decimal_places=2, verbose_name="女生价格")
    vip_price = DecimalField(
        default=Decimal(0), decimal_places=2, verbose_name="VIP价格")

    join_level_discount = BooleanField(default=True, verbose_name="参加会员折扣")

    # 报名人员填写信息
    need_nickname = BooleanField(default=False, verbose_name="需要昵称")
    need_mobile = BooleanField(default=False, verbose_name="需要手机")
    need_gender = BooleanField(default=False, verbose_name="需要性别")
    need_name = BooleanField(default=False, verbose_name="需要姓名")
    need_identification = BooleanField(default=False, verbose_name="需要身份证")
    need_emergency_contact = BooleanField(
        default=False, verbose_name="需要紧急联系人")
    need_gps = BooleanField(default=False, verbose_name="是否实时地理位置")

    need_ext1_name = CharField(null=True, verbose_name="扩展属性1名称")
    need_ext1_type = CharField(null=True,
                               verbose_name="扩展属性1类型",
                               choices=(('text', '文本'), ('photo', '照片')))

    need_ext2_name = CharField(null=True, verbose_name="扩展属性2名称")
    need_ext2_type = CharField(null=True,
                               verbose_name="扩展属性2类型",
                               choices=(('text', '文本'), ('photo', '照片')))

    need_ext3_name = CharField(null=True, verbose_name="扩展属性3名称")
    need_ext3_type = CharField(null=True,
                               verbose_name="扩展属性3类型",
                               choices=(('text', '文本'), ('photo', '照片')))

    visible = IntegerField(default=0, index=True, verbose_name="可见性",
                           choices=((0, "所有人"), (1, "仅成员")))

    refund_type = IntegerField(default=1, verbose_name="退款策略",
                               choices=((0, "开始前可以退款"), (1, "报名截止前可退"), (2, "不能退款")))

    created = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated = DateTimeField(default=datetime.now, verbose_name="最后更新")
    finished = DateTimeField(null=True, verbose_name="结算时间")

    online_paid_amount = DecimalField(
        default=Decimal(0), verbose_name="在线支付收入")
    credit_paid_amount = DecimalField(
        default=Decimal(0), verbose_name="余额支付收入")
    cash_paid_amount = DecimalField(default=Decimal(0), verbose_name="现金支付收入")
    free_times_amount = IntegerField(default=0, verbose_name="次卡支付数量")

    parent_id = IntegerField(default=0)
    state = IntegerField(default=ActivityState.opening, index=True)

    class Meta:
        db_table = 'activity'
        order_by = ('-id', )

    @property
    def creator_id(self):
        return self._data['creator']

    @property
    def team_id(self):
        return self._data['team_id']

    @property
    def sport_id(self):
        return self._data['sport']

    def is_ended(self):
        return self.end_time and datetime.now() > self.end_time

    def is_started(self):
        return self.start_time and datetime.now() > self.start_time

    def is_finished(self):
        """活动已结算
        """
        return self.state == self.ActivityState.finished

    def can_cancel(self):
        if self.state in (self.ActivityState.finished,
                          self.ActivityState.cancelled) \
                or self.is_ended():
            return False

        return True

    def can_change(self):
        return self.can_cancel()

    def can_apply(self):
        if self.state != self.ActivityState.opening:
            return "活动已经取消或结束"

        if (self.join_end, self.start_time)[True] < datetime.now():
            return "活动已报名截止"

        if self.members_count >= self.max_members:
            return "活动人数已满"

        return True

    @property
    def state_name(self):
        if self.state in (self.ActivityState.closed,
                          self.ActivityState.cancelled,
                          self.ActivityState.finished):
            return self.STATES.get(self.ActivityState(self.state), "未知")

        if datetime.now() > self.end_time:
            return "待结算"

        if self.members_count >= self.max_members:
            return "已满员"

        if (self.join_end, self.start_time)[True] < datetime.now():
            return "已截止"

        return "报名中"

    def add_member(self, user_id, users_count,
                   price, free_times, total_fee, order_id=0, order_no="",
                   payment_method="", payment_state=0, state=0, gps_enabled=True,
                   join_type="", inviter=None,
                   **extra_fields):
        """ 添加成员

            Args:
                user_id: 用户ID
                users_count: 报名人数
                price: 报名价格（记录报名时的价格）
                free_times: 使用次卡点数
                total_fee: 总计费用=price(users_count-free_times)
                order_id: 订单ID
                order_no: 订单NO
                payment_state: 支付状态
                payment_method: 支付方法
                state: 状态（ActivityMemberState）
                gps_enabled: gps是否开始
                join_type: 报名类型,标记报名用户来源
                inviter: 邀请码

        """

        activity_member = Activity.get_member(self.id, user_id)

        if activity_member is not None:
            raise Exception("不能重复报名")

        ActivityMember.create(
            team_id=self.team_id,
            user=user_id,
            activity=self,
            created=datetime.now(),
            gps_enabled=gps_enabled,
            state=state,
            join_type=join_type,
            users_count=users_count,
            price=price,
            free_times=free_times,
            total_fee=total_fee,
            order_id=order_id,
            order_no=order_no,
            payment_method=payment_method,
            payment_state=payment_state,
            inviter=inviter,
            **extra_fields,
        )

        Activity.update(
            members_count=Activity.members_count + users_count
        ).where(
            Activity.id == self.id
        ).execute()

    def leave(self, user):
        """ 用户退出活动

            用户退出活动后如果已支付需要退款,将订单修改为申请退款状态并删除活动成员信息
            Args:
                user: 用户对象
        """

        with(self._meta.database.transaction()):
            member = Activity.get_member(self.id, user.id)

            # 如果已支付需要退款
            if member.payment_state == TeamOrder.OrderState.TRADE_BUYER_PAID:
                member.refund()

            ActivityMember.delete().where(
                (ActivityMember.activity == self
                 ) & (ActivityMember.user == user.id)
            ).execute()

            Activity.update(
                members_count=Activity.get_members_count(self.id)
            ).where(
                Activity.id == self.id
            ).execute()

    def get_members(self, state=None):
        """ 获取活动成员列表

            Args:
                state: 指定状态

            Returns:
                Query
        """

        q = User.select(
            User, ActivityMember
        ).join(
            ActivityMember, on=ActivityMember.user
        ).where(
            ActivityMember.activity == self
        )

        if state is not None:
            q = q.where(ActivityMember.state == state)

        q = q.order_by(
            ActivityMember.nickname.asc(),
            User.name.asc()
        )

        return q

    @classmethod
    def update_members_count(cls, activity_id):
        """ 更新活动成员数量统计 """

        Activity.update(
            members_count=cls.get_members_count(activity_id)
        ).where(
            Activity.id == activity_id
        ).execute()

    @classmethod
    def get_members_count(cls, activity_id):
        """ 统计活动成员数量 """

        return ActivityMember.select(
            fn.SUM(ActivityMember.users_count)
        ).where(
            ActivityMember.activity == activity_id,
            ActivityMember.state == ActivityMember.ActivityMemberState.confirmed
        ).scalar() or 0

    @classmethod
    def is_member(cls, activity_id, user_id):
        """ 判断用户是否已报名指定活动场次
        """
        return ActivityMember.select().where(
            ActivityMember.user == user_id,
            ActivityMember.activity == activity_id
        ).exists()

    @classmethod
    def get_member(cls, activity_id, user_id):
        try:
            return ActivityMember.select().where(
                (ActivityMember.activity == activity_id) &
                (ActivityMember.user == user_id)
            ).get()

        except ActivityMember.DoesNotExist:
            return None

    def remove(self):
        """删除活动

            不允许删除已有用户报名的活动
            TODO:删除头像和照片
        """

        with(self.db.transaction()):

            ActivityMember.delete().where(
                ActivityMember.activity == self
            ).execute()

            self.redis.delete("yy:activity:followers:%s" % self.id)
            self.redis.delete("yy:activity:members:%s" % self.id)
            self.redis.delete("yy:activity:comments:%s" % self.id)
            self.redis.hdel("yy:activity:views_count", self.id)

            self.delete_instance()

    @cached_property
    def info(self):
        _info = self.to_dict(exclude=[Activity.creator, Activity.team,
                                      Activity.leader, Activity.sport])
        _info['creator_id'] = self._data['creator']
        _info['team_id'] = self._data['team']
        _info['leader_id'] = self._data['leader']
        _info['sport'] = Sport.get(id=self.sport_id).info if self.sport_id else {}
        return _info

    def get_info(self):
        return self.info


class ActivityMember(BaseModel):

    class ActivityMemberState(IntEnum):
        cancelled = -1  # 用户取消订单
        wait_confirm = 0  # 需要支付的活动未支付前, 不需要支付的活动如果需要审核的审核前为此状态
        confirmed = 1  # 支付成功或审核通过
        rejected = 2
        blocked = 3  # 黑名单用户不允许再报名参加此活动

    STATES = {
        ActivityMemberState.cancelled: "已取消",
        ActivityMemberState.wait_confirm: "待确认",
        ActivityMemberState.confirmed: "已确认",
        ActivityMemberState.rejected: "拒绝",
        ActivityMemberState.blocked: "黑名单",
    }

    activity = ForeignKeyField(Activity, related_name="members")

    user = ForeignKeyField(User, related_name="user_activities", null=True)
    team_id = IntegerField(default=0, verbose_name="俱乐部ID")

    order_id = IntegerField(
        default=0, verbose_name="订单号", help_text="无需支付的活动不创建订单")
    order_no = CharField(default="", max_length=64, null=True, verbose_name="订单编号")

    nickname = CharField(default="", null=True, max_length=128)
    mobile = CharField(default="", null=True, max_length=20)
    realname = CharField(default="", null=True, max_length=20)
    gender = CharField(default="", null=True, max_length=1)

    identification = CharField(
        default="", null=True, max_length=20, verbose_name="身份证号")
    emergency_contact = CharField(
        default="", null=True, max_length=20, verbose_name="紧急联系电话")

    info_ext1 = TextField(default="", null=True)
    info_ext2 = TextField(default="", null=True)
    info_ext3 = TextField(default="", null=True)

    inviter = ForeignKeyField(User, related_name="inviters",
                              null=True, verbose_name="邀请人")

    push_enabled = BooleanField(default=True, verbose_name="")
    gps_enabled = BooleanField(default=False)

    users_count = IntegerField(default=1, verbose_name="报名人数")
    free_times = IntegerField(default=0)

    price = DecimalField(default=Decimal(0),
                         verbose_name="报名价格",
                         help_text="由于活动价格有可能会发生变化,记录用户报名的价格"
                         )
    total_fee = DecimalField(decimal_places=2, verbose_name="应付总金额")

    join_type = CharField(max_length=16,
                          default="app",
                          help_text="报名方式 可选：weixin app")

    payment_method = CharField(
        null=True, help_text="支付方式 alipay weixin offline")
    payment_state = IntegerField(default=0, verbose_name="支付状态")

    state = IntegerField(default=0, verbose_name="状态", help_text="0 待确认 1 已确认 2 拉黑 3 拒绝")

    paid = DateTimeField(null=True, verbose_name="支付完成时间")
    created = DateTimeField(null=True, verbose_name="创建时间")
    confirmed = DateTimeField(null=True, verbose_name="确认时间")

    checkin_time = DateTimeField(null=True, verbose_name="签到时间")

    class Meta:
        db_table = 'activity_member'
        order_by = ('-created', )

        indexes = (
            (('user', 'activity'), True),
        )

    def get_image_url(self):
        pass

    @property
    def activity_id(self):
        return self._data['activity']

    @property
    def user_id(self):
        return self._data['user']

    def get_info(self):
        extra_fields = (ActivityMember.info_ext1, ActivityMember.info_ext2,
                        ActivityMember.info_ext3)
        exclude = [ActivityMember.activity, ActivityMember.user,
                   ActivityMember.inviter]
        exclude.extend(extra_fields)
        info = self.to_dict(exclude=exclude)

        # ForeignKeyField 只显示 ID
        info['activity_id'] = self._data['activity']
        info['user_id'] = self._data['user']
        info['inviter_id'] = self._data['inviter']

        # 自定义字段
        activity_extra_fields = {
            'info_ext1': self.activity.need_ext1_type,
            'info_ext2': self.activity.need_ext2_type,
            'info_ext3': self.activity.need_ext3_type
        }
        for name, _type in activity_extra_fields.items():
            if _type == 'photo':
                info[name] = self.get_attach_url(getattr(self, name))
            else:
                info[name] = getattr(self, name)

        return info

    @property
    def gender_label(self):
        return User.GENDERS.get(self.gender, "未知")

    @property
    def state_name(self):
        return self.STATES.get(self.state, "未知")

    @property
    def payment_state_label(self):
        return TeamOrder.ORDER_STATES.get(self.payment_state, "未知")

    def get_ext_info(self, name, ext_type):
        if ext_type == "photo":
            return self.get_image_url(getattr(self, name))

        return getattr(self, name)

    def refund(self, reason=""):
        """ 退款
        """
        # 未支付或已退款，无需退款
        if TeamOrder.OrderState(self.payment_state) != TeamOrder.OrderState.TRADE_BUYER_PAID:
            return True

        order = TeamOrder.get_or_none(id=self.order_id)
        if order is None:
            return True

        # 退款
        order.refund(reason=reason, free_times=self.free_times)

        return True
