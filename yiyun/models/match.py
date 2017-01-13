import logging
from collections import deque
from datetime import datetime
from decimal import Decimal
from enum import IntEnum, Enum
from typing import Union

from cached_property import cached_property
from peewee import (CharField, TextField, DateTimeField,
                    IntegerField, BooleanField, ForeignKeyField,
                    DecimalField, DoubleField, SelectQuery, JOIN_LEFT_OUTER)

from yiyun.core import current_app as app, celery
from yiyun.ext.database import (JSONTextField, ListField, PointField)
from yiyun.models import Sport, ChinaCity
from .base import BaseModel


class Match(BaseModel):
    """ 赛事
    """

    class Meta:
        db_table = 'match'
        order_by = ('-id', )

        indexes = (
            (('lat', 'lng'), False),
        )

    # 赛事状态可选值
    class MatchState(IntEnum):
        closed = -1
        cancelled = 0
        wait_review = 5
        rejected = 10
        in_review = 15
        opening = 20
        finished = 100

    STATES = {
        MatchState.closed: "已关闭",
        MatchState.cancelled: "已取消",
        MatchState.wait_review: "等待审核",
        MatchState.rejected: "审核拒绝",
        MatchState.in_review: "正在审核",
        MatchState.opening: "进行中",
        MatchState.finished: "已结束"
    }

    REFUND_TYPES = {
        0: "开始前可以退款",
        1: "报名截止前可退",
        2: "不能退款",
    }

    team_id = IntegerField(index=True)
    user_id = IntegerField(index=True)
    type = IntegerField(default=0,
                        verbose_name="赛事类型",
                        help_text="对战型如：足球、蓝球，非对战型：跑步、自行车",
                        choices=((0, "对战型"), (1, "非对战型")))

    title = CharField(max_length=180, index=True, verbose_name="标题")
    cover_key = CharField(null=True, verbose_name="海报")

    sport_id = IntegerField()
    score_unit = CharField(default="", verbose_name="成绩单位")

    contact_person = CharField(default="", max_length=120, verbose_name="联系人")
    contact_phone = CharField(default="", max_length=120, verbose_name="联系电话")
    contact = TextField(default="", verbose_name="联系方式")

    description = TextField(null=False, verbose_name="描述")
    rules = TextField(default="", verbose_name="赛事规程")
    reward = CharField(default="", verbose_name="奖励说明")

    country = CharField(default="中国", max_length=128)
    province = CharField(default="", max_length=128,
                         choices=ChinaCity.get_provinces(),
                         verbose_name="省份")

    city = CharField(default="", max_length=128, index=True,
                     verbose_name="城市",
                     choices=[])

    address = CharField(default="", max_length=250, verbose_name="举办地址")

    lat = DoubleField(default=0)
    lng = DoubleField(default=0)
    location = PointField(null=True)
    geohash = CharField(default="", index=True, max_length=16)

    # gym_id = IntegerField(default=0, verbose_name="场馆ID")

    join_type = IntegerField(default=0, choices=((0, "个人"), (1, "团队")))
    max_members = IntegerField(default=0, verbose_name="人数限制")
    members_count = IntegerField(default=0)

    group_type = IntegerField(default=0, choices=((0, "不分"), (1, "分")))

    recommend_time = IntegerField(default=0, verbose_name="推荐时间")
    recommend_region = IntegerField(default=0, verbose_name="推荐范围",
                                    choices=((0, "全国"), (1, "同城")))

    payment_type = IntegerField(default=0,
                                verbose_name="支付方式",
                                help_text="0 在线支付 1 线下支付 2 均可")

    start_time = DateTimeField(null=True, verbose_name="开始时间")
    end_time = DateTimeField(null=True, verbose_name="结束时间")
    duration = IntegerField(default=0,
                            verbose_name="活动持续时间",
                            help_text="自动根据开始和结束时间计算")

    join_start = DateTimeField(null=True, verbose_name="报名开始时间")
    join_end = DateTimeField(null=True, verbose_name="报名截止时间")

    cancelled = DateTimeField(null=True, verbose_name="取消时间")
    cancel_reason = TextField(default="", verbose_name="取消原因")

    reject_time = DateTimeField(null=True, verbose_name="")
    reject_reason = TextField(default="")

    verified = BooleanField(default=False, index=True)
    verify_reason = CharField(default="", max_length=250)

    price = DecimalField(default=Decimal(0),
                         decimal_places=2,
                         verbose_name="报名费")

    refund_type = IntegerField(default=1,
                               verbose_name="退款策略",
                               choices=((0, "开始前可以退款"),
                                        (1, "报名截止前可退"),
                                        (2, "不能退款")))

    created = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated = DateTimeField(default=datetime.now, verbose_name="最后更新")
    finished = DateTimeField(null=True, verbose_name="结算时间")

    fields = ListField(default=[], verbose_name="报名表系统选项")
    # 已经上线的活动被修改的时候 会被复制一份
    # 在被复制的活动审核通过的时候 被修改的内容会被更新到 原活动
    wait_review_for_match = IntegerField(default=0,
                                         verbose_name="原活动")
    state = IntegerField(default=MatchState.wait_review,
                         verbose_name="赛事状态")
    pushed = DateTimeField(null=True, help_text="赛事开始通知是否推送")

    @cached_property
    def join_type_name(self):
        if self.join_type == 0:
            return "个人"

        return "团队"

    @cached_property
    def group_type_name(self):
        if self.group_type == 0:
            return "不分组"

        return "分组"

    @cached_property
    def refund_type_name(self):
        return self.REFUND_TYPES.get(self.refund_type, "未知")

    @cached_property
    def refund_expire(self):
        if self.refund_type == 0:
            return self.start_time

        elif self.refund_type == 1:
            return self.join_end or self.start_time

        return None

    @cached_property
    def sport_name(self):
        if not self.sport_id:
            return ""

        sport = Sport.get_or_none(id=self.sport_id)

        return sport.name if sport else ""

    @cached_property
    def sport(self):
        if not self.sport_id:
            return None

        return Sport.get_or_none(id=self.sport_id)

    @property
    def field_names(self):
        names = []
        for field in self.fields:
            names.append(MatchOption.get_builtin_field_name(field))

        return names

    def query_custom_options(self):
        """
        查询自定义选项,返回查询对象Query
        """
        # 获取自定义选项
        query = MatchOption.select().where(
            MatchOption.match_id == self.id
        ).order_by(
            MatchOption.sort_num.desc()
        )
        return query

    @cached_property
    def custom_options_list(self):
        """
        获取赛事报名自定义选项列表
        """
        options = []
        for option in self.query_custom_options():
            assert isinstance(option, MatchOption)
            options.append(option.info)
        return options

    @cached_property
    def option_info_list(self):
        """
        获取选项信息列表
        """
        class OptionInfoDisplayObject(object):

            def __init__(self, option_type: Union[MatchOption.BuiltinFieldTypes,
                                                  MatchOption.CustomFieldTypes],
                         option_key: str, option_name: str):
                self.option_type = option_type
                self.option_key = option_key
                self.option_name = option_name

            def get_option_value(self, source):
                return source.get_option_value(self.option_type,
                                               self.option_key)

            def is_avatar(self):
                if self.option_type is MatchOption.BuiltinFieldTypes.Avatar:
                    return True
                return False

            def is_idcard_photo(self):
                if self.option_type is MatchOption.BuiltinFieldTypes.IdcardPhoto:
                    return True
                return False

            def is_leader_check(self):
                if self.option_type is MatchOption.BuiltinFieldTypes.IsLeader:
                    return True
                return False

            def is_gender(self):
                if self.option_type is MatchOption.BuiltinFieldTypes.Gender:
                    return True
                return False

            def is_photo(self):
                if self.option_type is MatchOption.CustomFieldTypes.Photo:
                    return True
                return False

            def is_file(self):
                if self.option_type is MatchOption.CustomFieldTypes.File:
                    return True
                return False

            def is_boolean(self):
                if self.option_type is MatchOption.CustomFieldTypes.Boolean:
                    return True
                return False

            def __repr__(self):
                return "OptionInfoDisplayObject(option_type:(%s), " \
                       "option_key:(%s), option_name:(%s))" \
                       % (self.option_type, self.option_key,
                          self.option_name)

        option_list = deque()
        # 获取内置选项
        for field in self.fields:
            item = OptionInfoDisplayObject(
                MatchOption.BuiltinFieldTypes(field),
                field,
                MatchOption.get_builtin_field_name(field),
            )
            if MatchOption.judge_builtin_field(field,
                                               MatchOption.BuiltinFieldTypes.Avatar):
                option_list.appendleft(item)
            else:
                option_list.append(item)

        # 获取自定义选项
        for option in self.query_custom_options():
            assert isinstance(option, MatchOption)
            custom_item = OptionInfoDisplayObject(
                MatchOption.CustomFieldTypes(option.field_type),
                str(option.id),
                str(option.title)
            )
            option_list.append(custom_item)

        return option_list

    def is_wait_review(self):
        return self.state == self.MatchState.wait_review

    def can_change_goups(self):
        """ 上架前的赛事可以修改分组列表
        """
        return self.state in (self.MatchState.wait_review,
                              self.MatchState.rejected)

    def can_change(self):
        """ 结算、取消和关闭的赛事不能再修改
        """
        return self.state not in (self.MatchState.finished,
                                  self.MatchState.cancelled,
                                  self.MatchState.closed)

    def can_cancel(self):
        """ 结束前可以取消 """
        if self.MatchState.cancelled.value < self.state <= \
                self.MatchState.opening.value:
            return True
        return False

    def can_leave(self) -> bool:
        """
        进行中的赛事可以退出
        :return: bool
        """
        if self.state != self.MatchState.opening.value:
            logging.debug("不能退赛, 赛事状态为: {0}".format(self.state))
            return False
        now = datetime.now()

        # 赛事开始前可退出
        if self.refund_type == 0 and self.start_time > now:
            return True

        # 报名截至前可退出
        elif self.refund_type == 1 and self.join_end > now:
            return True
        else:
            return False

    @cached_property
    def open_for_join(self):

        if self.MatchState != self.MatchState.opening:
            return False

        if self.members_count >= self.max_members:
            return False

        if datetime.now() >= self.join_end:
            return False

        if datetime.now() < self.join_start:
            return False

        return True

    @cached_property
    def is_finished(self):
        return datetime.now() >= self.end_time

    @cached_property
    def is_join_end(self):
        return datetime.now() >= self.join_end

    def can_apply_settlement(self):
        if self.is_join_end:
            return True
        else:
            return False

    @cached_property
    def state_name(self):
        if self.state != self.MatchState.opening:
            return self.STATES.get(self.state, "未知")

        time_now = datetime.now()

        if self.join_start and time_now < self.join_start:
            return "等待报名开始"

        if self.start_time < time_now < self.end_time:
            return "进行中"

        if time_now <= self.join_end:
            return "报名中"

        if self.join_end < time_now < self.start_time:
            return "报名截止"

        if time_now >= self.end_time:
            return "已结束"

        if self.members_count >= self.max_members and \
                time_now < self.join_end:
            return "已报满"

        return "未知"

    def can_join(self):

        if self.state == self.MatchState.finished:
            return {
                "can": False,
                "reason": "赛事已结束"
            }

        elif self.state == self.MatchState.cancelled:
            return {
                "can": False,
                "reason": "赛事已取消"
            }

        elif self.state != self.MatchState.opening:
            return {
                "can": False,
                "reason": "赛事尚未通过审核"
            }

        elif self.join_start and self.join_start > datetime.now():
            return {
                "can": False,
                "reason": "报名未开始"
            }

        elif (self.join_end and self.join_end < datetime.now()
              ) or (not self.join_end and self.start_time < datetime.now()):

            return {
                "can": False,
                "reason": "报名已截止"
            }

        elif self.members_count >= self.max_members:
            return {
                "can": False,
                "reason": "已报满"
            }

        return {
            "can": True,
            "reason": ""
        }

    @property
    def cover(self):
        cover_url = app.settings['avatar_url'].rstrip('/')
        return Match.get_cover_urls(self.cover_key, cover_url, crop=False)

    @property
    def icon(self):
        cover_url = app.settings['avatar_url'].rstrip('/')
        return Match.get_cover_urls(self.cover_key, cover_url, crop=True)

    @cached_property
    def list_info(self):
        info = self.to_dict(
            exclude=[Match.geohash, Match.cover_key, Match.description,
                     Match.rules, Match.fields, Match.contact,
                     Match.contact, Match.duration, Match.location,
                     Match.wait_review_for_match]
        )

        info['cover'] = self.cover
        info['icon'] = self.icon
        info['open_for_join'] = self.open_for_join
        info['state_name'] = self.state_name

        return info

    @classmethod
    def update_members_count(cls, match_id):
        Match.update(
            members_count=MatchMember.select().where(
                MatchMember.match_id == match_id,
                MatchMember.state == MatchMember.MatchMemberState.normal
            ).count()
        ).where(
            Match.id == match_id
        ).execute()

    def leave_request(self, member):
        """申请退赛"""
        MatchMember.update(state=MatchMember.MatchMemberState.leave.value)\
            .where(MatchMember.id == member.id).execute()

    def leave(self, member):
        """
        执行退出赛事操作
        :param insists:
        :param member: MatchMember instance
        :return:
        """
        with Match._meta.database.transaction():
            member.delete_instance()
            self.update_members_count(match_id=self.id)
            if member.group_id:
                MatchGroup.update_members_count(group_id=member.group_id)


class MatchLog(BaseModel):
    """ 赛事日志
    """

    class Meta:
        db_table = 'match_log'

    match_id = IntegerField()
    content = TextField()
    operator_id = IntegerField()
    created = DateTimeField(default=datetime.now, verbose_name="创建时间")


class MatchGroup(BaseModel):
    """ 赛事分组
    """

    class Meta:
        db_table = 'match_group'

        indexes = (
            (('match_id', 'name'), False),
        )

    match_id = IntegerField()
    name = CharField()
    price = DecimalField(default=Decimal(0),
                         decimal_places=2,
                         verbose_name="报名费")

    max_members = IntegerField()
    members_count = IntegerField(default=0)
    team_members_count = IntegerField(default=0, verbose_name="团队人数要求")

    sort_num = IntegerField(default=0)

    @classmethod
    def update_members_count(cls, group_id):
        MatchGroup.update(
            members_count=MatchMember.select().where(
                MatchMember.group_id == group_id,
                MatchMember.state == MatchMember.MatchMemberState.normal
            ).count()
        ).where(
            MatchGroup.id == group_id
        ).execute()

    @cached_property
    def info(self):
        return self.to_dict(
            only=[MatchGroup.id, MatchGroup.name, MatchGroup.price,
                  MatchGroup.max_members]
        )


class MatchCover(BaseModel):
    """ 赛事海报列表
    """

    class Meta:
        db_table = 'match_cover'

    POSITION_NAMES = (('description', "赛事详情"),
                      ('statuses', "赛事战报"),
                      ('rules', '赛事规程'),
                      ('rounds', '赛事赛程')
                      )

    match_id = IntegerField(index=True)
    position = CharField(choices=POSITION_NAMES)
    cover_key = CharField()
    created = DateTimeField(default=datetime.now)

    @property
    def position_name(self):
        fields = dict(self.POSITION_NAMES)
        return fields.get(self.position, "未知")

    @property
    def cover(self):
        cover_url = app.settings['avatar_url'].rstrip('/')
        return MatchCover.get_cover_urls(self.cover_key, cover_url, crop=False)

    @cached_property
    def info(self):
        info = self.to_dict(
            only=[MatchCover.position]
        )

        if self.cover_key:
            info['cover'] = self.cover

        return info


class MatchOption(BaseModel):
    """ 赛事报名表选项
    """

    class Meta:
        db_table = 'match_option'

    class BuiltinFieldTypes(Enum):
        """报名表内置选项可选类型枚举"""
        Name = "name"
        Gender = "gender"
        Age = "age"
        Mobile = "mobile"
        IsLeader = "is_leader"
        IdcardNumber = "idcard_number"
        IdcardPhoto = "idcard_photo"
        Avatar = "avatar"

    BUILT_IN_TYPE_NAMES = {
        BuiltinFieldTypes.Name: "名称",
        BuiltinFieldTypes.Gender: "性别",
        BuiltinFieldTypes.Age: '年龄',
        BuiltinFieldTypes.Mobile: "手机",
        BuiltinFieldTypes.Avatar: "头像",
        BuiltinFieldTypes.IdcardNumber: "证件号码",
        BuiltinFieldTypes.IdcardPhoto: "证件照片",
        BuiltinFieldTypes.IsLeader: "是否为队长"
    }

    class CustomFieldTypes(Enum):
        """报名表自定义选项可选类型枚举"""
        Text = "text"
        Number = "number"
        Textarea = "textarea"
        Choice = "choice"
        Photo = "photo"
        Boolean = "boolean"
        File = "file"

    FIELD_TYPES = ((CustomFieldTypes.Text.value, '文本'),
                   (CustomFieldTypes.Number.value, '数字'),
                   (CustomFieldTypes.Textarea.value, "多段文本"),
                   (CustomFieldTypes.Choice.value, "单选"),
                   # ("multichoice", "多选"),
                   (CustomFieldTypes.Photo.value, "照片"),
                   (CustomFieldTypes.Boolean.value, "布尔值"),
                   (CustomFieldTypes.File.value, "文件"))

    match_id = IntegerField()
    title = CharField()
    field_type = CharField(verbose_name="类型", choices=FIELD_TYPES)

    required = BooleanField(default=False)
    choices = CharField(default="")
    sort_num = IntegerField(default=0)

    @classmethod
    def get_builtin_field_name(cls, field: Union[str, BuiltinFieldTypes]):
        """
        获取某个'内置选项可选类型(BuiltinFieldTypes)'外部表现名字
        """
        field_type = cls.BuiltinFieldTypes(field)
        return cls.BUILT_IN_TYPE_NAMES.get(field_type, "未知")

    @classmethod
    def judge_builtin_field(cls, field: Union[str, BuiltinFieldTypes],
                            target_field: BuiltinFieldTypes):
        """
        判断field是否是某一个'内置选项可选类型(BuiltinFieldTypes)'
        """
        field = cls.BuiltinFieldTypes(field)
        return field is target_field

    @classmethod
    def judge_custom_field(cls, field: Union[str, CustomFieldTypes],
                           target_field: CustomFieldTypes):
        """
        判断field是否是某一个'自定义选项可选类型(CustomFieldTypes)'
        """
        field = cls.CustomFieldTypes(field)
        return field is target_field

    @property
    def field_type_name(self):
        fields = dict(self.FIELD_TYPES)
        return fields.get(self.field_type, "未知")

    @cached_property
    def info(self):
        info = self.to_dict(
            only=[MatchOption.id, MatchOption.title, MatchOption.field_type,
                  MatchOption.required]
        )

        if self.field_type in ('choice', 'multichoice'):
            choices = self.choices.replace("丨", "|")
            info['choices'] = choices.split("|")

        return info


class MatchStatus(BaseModel):
    """赛事动态"""

    class Meta:
        db_table = 'match_status'

    match_id = IntegerField()
    is_notice = BooleanField(default=False, help_text="")
    content = TextField(help_text="")
    photos = ListField()

    comments_count = IntegerField(default=0)
    created = DateTimeField(default=datetime.now)
    like_count = IntegerField(default=0, help_text="点赞数量")

    def do_like(self, user_id):
        """
        点赞
        :param user_id:
        :return:
        """
        with MatchStatus._meta.database.transaction():
            MatchStatusLike.create(status=self, user_id=user_id)
            self.like_count += 1
            self.save(only=self.dirty_fields)
        return self

    def undo_like(self, user_id):
        """
        取消点赞
        :param user_id:
        :return:
        """
        with MatchStatus._meta.database.transaction():
            rows = MatchStatusLike.delete()\
                .where(MatchStatusLike.status == self,
                       MatchStatusLike.user_id == user_id)\
                .execute()
            self.like_count -= rows
            if self.like_count < 0:
                self.like_count = 0
            self.save(only=self.dirty_fields)
            return self

    def get_likes(self) -> SelectQuery:
        """
        获取点赞列表
        :return:
        """
        query = MatchStatusLike\
            .select(MatchStatusLike.status, MatchStatusLike.user_id)\
            .where(MatchStatusLike.status == self)\
            .order_by(MatchStatusLike.create_at.desc(),
                      MatchStatusLike.id.desc())\
            .distinct(MatchStatusLike.user_id)
        return query

    @property
    def photo_urls(self):
        photo_url = app.settings['attach_url'].rstrip('/')

        photo_urls = []
        for photo in self.photos:
            photo_urls.append(MatchStatus.get_cover_urls(photo, photo_url, crop=False))

        return photo_urls


class MatchComment(BaseModel):

    """赛事评论"""

    class Meta:
        db_table = 'match_comment'

    # match_id = IntegerField()
    match = ForeignKeyField(Match, related_name="comments")
    user_id = IntegerField()
    # status_id = IntegerField(default=0, help_text="如果是动态评论关联到动态")
    status = ForeignKeyField(MatchStatus, related_name="comments", null=True)
    reply_to_comment_id = IntegerField()
    reply_to_user_id = IntegerField()

    content = TextField()
    created = DateTimeField(default=datetime.now)


class MatchStatusLike(BaseModel):
    """
    赛事动态点赞
    """
    class Meta:
        db_table = "match_status_like"

    status = ForeignKeyField(MatchStatus, related_name="likes")
    user_id = IntegerField(default=0, help_text="点赞用户 id")
    create_at = DateTimeField(default=datetime.now)


class MatchMember(BaseModel):
    """ 参赛者信息

        参赛者可能为团队或个人
    """

    class Meta:
        db_table = 'match_member'

        indexes = (
            (('match_id', 'user_id'), False),
        )

    class MatchMemberState(IntEnum):
        banned = -1
        wait_pay = 0
        wait_review = 5
        normal = 10
        leave = 15

    MATCH_MEMBER_STATES = {
        MatchMemberState.banned: "禁赛",
        MatchMemberState.wait_pay: "待支付",
        MatchMemberState.wait_review: "待审核",
        MatchMemberState.normal: "正常",
        MatchMemberState.leave: "退赛"
    }

    class MatchMemberApproveState(IntEnum):
        approved = 1
        not_approved = 0
        request_for_improved = -1
        reject = -2

    MATCH_MEMBER_APPROVE_STATE = {
        MatchMemberApproveState.approved: "审核通过",
        MatchMemberApproveState.not_approved: "未审核",
        MatchMemberApproveState.request_for_improved: "要求完善资料",
        MatchMemberApproveState.reject: "审核拒绝"
    }

    match_id = IntegerField()
    group_id = IntegerField()
    member_type = IntegerField(default=0,
                               verbose_name="类型",
                               choices=((0, "个人"), (1, "团队")))

    user_id = IntegerField(default=0,
                           verbose_name="用户ID")

    name = CharField(default="", max_length=128, verbose_name="用户名")
    mobile = CharField(default="", max_length=11, verbose_name="手机")
    gender = CharField(default="n", verbose_name="性别",
                       choices=(("f", "女"), ("m", "男"), ("n", "未知")))
    age = IntegerField(default=0, verbose_name="年龄")
    is_leader = BooleanField(default=False, verbose_name="是否为队长")
    avatar_key = CharField(default="", max_length=128)

    realname = CharField(default="", verbose_name="真实姓名")
    idcard_number = CharField(default="", max_length=64)
    idcard_front = CharField(default="", max_length=128)
    idcard_back = CharField(default="", max_length=128)

    extra_attrs = JSONTextField(verbose_name="扩展信息")

    source = CharField(default="")

    order_id = IntegerField(default=0)
    pt_order_no = CharField(default="", max_length=128, index=True)
    total_fee = DecimalField(decimal_places=2, verbose_name="订单金额")

    created = DateTimeField(default=datetime.now)

    # refund_type = IntegerField(default=0, help_text="0 无退款，1 已申请 2 已退款")
    state = IntegerField(default=0, help_text="-1 禁赛 0 待支付 1 待审核 10 正常 15 退赛")
    state_before_ban = IntegerField(default=0, help_text="恢复禁赛状态时，将恢复到此状态")

    approve_state = IntegerField(default=0, help_text="-2 审核拒绝 -1 要求完善资料 0 未审核 1 审核通过")

    def parse_extra(self):
        """ 解析自定义扩展信息
        """

        if not self.extra_attrs:
            return

        option_values = []
        for option_value in self.extra_attrs:
            value = option_value['value']

            if option_value.get("is_photo", False) and value:
                value = MatchMember.get_cover_urls(value, crop=False)

            option_values.append({
                "option_id": option_value['option_id'],
                "option_title": option_value['option_title'],
                "value": value,
            })
        return option_values

    def set_approved(self):
        self.approve_state = self.MatchMemberApproveState.approved

    def set_reject(self):
        self.approve_state = self.MatchMemberApproveState.reject

    def set_request_for_improved(self):
        self.approve_state = self.MatchMemberApproveState.request_for_improved

    @cached_property
    def approve_state_name(self):
        return self.MATCH_MEMBER_APPROVE_STATE.get(self.approve_state, "未知")

    @cached_property
    def approve_state_name(self):
        return self.MATCH_MEMBER_APPROVE_STATE.get(self.state, "未知")

    @cached_property
    def extra_attrs_mapping(self):
        extra_attrs = self.parse_extra()
        if extra_attrs:
            mapping = {str(attr["option_id"]): attr["value"] for attr in extra_attrs}
            return mapping
        else:
            return {}

    def get_option_value(self, option_type: Union[MatchOption.BuiltinFieldTypes,
                                                  MatchOption.CustomFieldTypes],
                         option_key: str):
        """
        获取报名选项值
        """
        if option_type in MatchOption.BuiltinFieldTypes:
            return self.get_builtin_option_value(option_type, option_key)
        elif option_type in MatchOption.CustomFieldTypes:
            return self.get_custom_option_value(option_key)
        else:
            return ""

    def get_builtin_option_value(self, option_type: MatchOption.BuiltinFieldTypes,
                                 option_key: str):
        """获取内置选项值，有特殊处理"""
        if MatchOption.judge_builtin_field(option_type,
                                           MatchOption.BuiltinFieldTypes.Avatar):
            option_value = MatchMember.get_cover_urls(self.avatar_key)
        elif MatchOption.judge_builtin_field(option_type,
                                             MatchOption.BuiltinFieldTypes.IdcardPhoto):
            option_value = {
                "idcard_front": MatchMember.get_cover_urls(self.idcard_front, crop=False),
                "idcard_back": MatchMember.get_cover_urls(self.idcard_back, crop=False)
            }
        elif MatchOption.judge_builtin_field(option_type,
                                             MatchOption.BuiltinFieldTypes.IsLeader):
            option_value = getattr(self, option_key, "")  # type: bool
        else:
            option_value = str(getattr(self, option_key, ""))

        return option_value

    def get_custom_option_value(self, option_key: str):
        option_value = self.extra_attrs_mapping.get(option_key, "")
        return option_value

    def display_gender(self):
        if self.gender == "m":
            return "男"
        elif self.gender == "f":
            return "女"
        else:
            return "保密"

    @cached_property
    def mini_avatar(self):
        """小头像地址"""
        return self.get_cover_url(self.avatar_key, "small")

    @cached_property
    def state_name(self):
        return self.MATCH_MEMBER_STATES.get(self.state, "未知")

    @cached_property
    def info(self):

        # 个人类型
        if self.member_type == 0:
            info = self.to_dict(
                exclude=[MatchMember.match_id, MatchMember.member_type,
                         MatchMember.source, MatchMember.avatar_key,
                         MatchMember.idcard_front, MatchMember.idcard_back,
                         MatchMember.state_before_ban]
            )

            if self.idcard_front:
                info['idcard_front'] = MatchMember.get_cover_urls(
                    self.idcard_front, crop=False)

            if self.idcard_back:
                info['idcard_back'] = MatchMember.get_cover_urls(
                    self.idcard_back, crop=False)

        # 团队类型
        elif self.member_type == 1:
            info = self.to_dict(
                exclude=[MatchMember.match_id, MatchMember.member_type,
                         MatchMember.source, MatchMember.avatar_key,
                         MatchMember.idcard_number, MatchMember.idcard_front,
                         MatchMember.idcard_back, MatchMember.age,
                         MatchMember.state_before_ban]
            )

        info['extra_attrs'] = self.parse_extra()
        if self.avatar_key:
            info['avatar'] = MatchMember.get_cover_urls(self.avatar_key)

        return info

    @cached_property
    def mini_info(self):

        # 个人类型
        if self.member_type == 0:
            info = self.to_dict(
                exclude=[MatchMember.match_id, MatchMember.member_type,
                         MatchMember.source, MatchMember.avatar_key,
                         MatchMember.idcard_front, MatchMember.idcard_back,
                         MatchMember.extra_attrs, MatchMember.state_before_ban]
            )

        # 团队类型
        elif self.member_type == 1:
            info = self.to_dict(
                exclude=[MatchMember.match_id, MatchMember.member_type,
                         MatchMember.source, MatchMember.avatar_key,
                         MatchMember.idcard_number, MatchMember.idcard_front,
                         MatchMember.idcard_back, MatchMember.age,
                         MatchMember.extra_attrs, MatchMember.state_before_ban]
            )

        info['avatar'] = MatchMember.get_cover_urls(self.avatar_key)

        return info

    @classmethod
    def query_all_members(cls, match_id):
        query = MatchMember.select(
            MatchMember,
            MatchGroup
        ).join(
            MatchGroup,
            join_type=JOIN_LEFT_OUTER,
            on=(MatchMember.group_id == MatchGroup.id).alias("group")
        ).where(
            MatchMember.match_id == match_id
        ).order_by(MatchMember.id.desc())

        return query


class MatchMemberOptionValue(BaseModel):
    """
    """

    class Meta:
        db_table = 'match_member_option_value'

    match_id = IntegerField()
    member_id = IntegerField()
    option_id = IntegerField()
    value = CharField(default="")


class MatchMemberProfile(BaseModel):

    """ 报名者
    """

    class Meta:
        db_table = 'match_member_profile'

    match_id = IntegerField()
    member_id = IntegerField()
    user_id = IntegerField()

    is_leader = BooleanField(default=False, verbose_name="是否为队长")

    name = CharField()
    mobile = CharField(default="", max_length=11)
    gender = CharField(default="n", max_length=1)
    avatar_key = CharField(default="", max_length=128)

    realname = CharField(default="")
    idcard_number = CharField(default="", max_length=64)
    idcard_front = CharField(default="", max_length=128)
    idcard_back = CharField(default="", max_length=128)

    extras = JSONTextField()

    state = IntegerField(default=0)


class MatchRound(BaseModel):
    """ 赛事轮次
    """

    class Meta:
        db_table = 'match_round'
        indexes = (
            (('match_id', 'group_id'), False),
        )

    match_id = IntegerField()
    group_id = IntegerField(default=0)

    name = CharField(max_length=200)
    description = TextField(default="")

    address = CharField(default="")
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)

    state = IntegerField(default=0)
    created = DateTimeField(default=datetime.now)

    @cached_property
    def info(self):
        info = self.to_dict(
            only=[MatchRound.id, MatchRound.name, MatchRound.start_time,
                  MatchRound.end_time, MatchRound.address]
        )

        return info


class MatchAgainst(BaseModel):

    """ 对阵关系
       left_member vs right_member
    """

    class Meta:
        db_table = 'match_against'

    match_id = IntegerField()
    round_id = IntegerField()

    left_member_id = IntegerField(verbose_name="主场")
    right_member_id = IntegerField(default=0, verbose_name="客场")
    left_score = CharField(default="", max_length=16)
    right_score = CharField(default="", max_length=16)
    win_member_id = IntegerField(default=0)

    address = CharField(default="", verbose_name="地址")
    referee = CharField(default="", verbose_name="裁判")
    comment = TextField(default="", verbose_name="点评")

    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)

    state = IntegerField(default=0)

    @cached_property
    def info(self):
        return self.to_dict(
            exclude=[MatchAgainst.match_id, MatchAgainst.state]
        )


class MatchStartCeleryTask(BaseModel):
    """
    记录比赛开始的 celery 任务
    比赛编辑了开始时间后需要终止之前提交的推送任务, 所以需要记录 task_id
    """
    class Meta:
        db_table = "match_start_celery_task"

    task_id = CharField(verbose_name="celery task_id")
    match_id = IntegerField(help_text="Match.id")
    created = DateTimeField(default=datetime.now)
    done = DateTimeField(null=True)

    @classmethod
    def terminate_if_necessary(cls, match_id: int):
        """如果任务存在并且为完成, 终止任务"""
        tasks = cls.select().where(cls.done.is_null(),
                                   cls.match_id == match_id)
        for task in tasks:
            celery.control.revoke(task.task_id, terminate=True)

        cls.delete().where(cls.done.is_null(), cls.match_id == match_id)\
            .execute()

    @classmethod
    def task_exist(cls, task_id: str=None, match_id: int=None) -> bool:
        """任务是否存在"""
        assert task_id or match_id, "`task_id` 和 `match_id` 不能同时为空"
        query = cls.select().where(cls.done.is_null())
        if task_id:
            query = query.where(cls.task_id == task_id)
        if match_id:
            query = query.where(cls.match_id == match_id)
        return query.exists()

    @classmethod
    def task_done(cls, task_id):
        """任务执行成功后调用"""
        return cls.update(done=datetime.now()).where(cls.task_id == task_id)\
            .execute()

    @classmethod
    def new_task(cls, task_id, match_id):
        """
        新任务记录
        :param task_id:
        :param match_id:
        :return:
        """
        inst = cls.create(task_id=task_id, match_id=match_id)
        return inst

    @classmethod
    def task_terminal(cls, task_id):
        """任务被终止"""
        return cls.delete().where(cls.task_id == task_id).execute()


class ApplicationState(IntEnum):
    disapproved = -1
    requesting = 1
    approved = 2
    finished = 10


class SettlementApplication(BaseModel):
    """
    赛事清算申请
    主办方提交清算申请, 管理审核通过后添加结算任务
    """

    APPLICATION_PROCESSING_STATES = {
        ApplicationState.approved: "已批准",
        ApplicationState.disapproved: "已驳回",
        ApplicationState.finished: "已经结束",
        ApplicationState.requesting: "已请求"
    }

    class Meta:
        db_table = "settlement_application"

    match_id = IntegerField(help_text="赛事 Match.id")
    team_id = IntegerField(help_text="主办方 Team.id")
    user_id = IntegerField(help_text="申请人 User.id")
    balance = DecimalField(help_text="结算金额", default=0, decimal_places=2)
    created = DateTimeField(default=datetime.now, help_text="申请时间")
    approve_at = DateTimeField(null=True, help_text="审批时间")
    processing = IntegerField(help_text="申请状态",
                              default=ApplicationState.requesting.value)
    admin_id = IntegerField(help_text="审核人 Admin.id", null=True)

    @property
    def processing_state_name(self):
        return self.APPLICATION_PROCESSING_STATES.get(self.processing, "未知")

    def is_requesting(self):
        return self.processing == ApplicationState.requesting

    @classmethod
    def is_application_exist(cls, match_id):
        # 指定的赛事是不是已经存在申请记录
        application = SettlementApplication.select()\
            .where(SettlementApplication.match_id == match_id,
                   SettlementApplication.processing >= ApplicationState
                   .requesting.value)

        if application.exists():
            return True
        else:
            return False
