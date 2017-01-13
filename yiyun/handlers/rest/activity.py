import datetime
import logging
import time

import copy
import geohash
import hashlib
from peewee import fn, JOIN_LEFT_OUTER
from tornado import gen

from yiyun import tasks
from yiyun.exceptions import ArgumentError
from yiyun.ext.mixins import AMapMixin
from yiyun.libs.peewee_filter import (Filter, Filtering, StringFiltering,
                                      ForeignKeyFiltering, DateCondition,
                                      SortFilter)
from yiyun.libs.peewee_serializer import SerializerField
from yiyun.libs.wxpay import WxPayMixin
from .schemas import activity as schema
from yiyun.models import (User, Activity, TeamOrder, ActivityMember, Team,
                          TeamMember, Sport)
from yiyun.service.team import TeamMemberService
from .base import (rest_app, BaseClubAPIHandler, ApiException, authenticated,
                   validate_arguments_with)
from .schemas import activity as schemas
from .serializers.activity import (Serializer, ActivitySerializer,
                                   SecureActivityMemberSerializer,
                                   InsecureActivityMemberSerializer,
                                   SimpleActivitySerializer,
                                   InsecureActivityMemberSerializer)
from .serializers.order import OrderSimpleSerializer

from yiyun.service.team import TeamMemberService


class ActivitySearchFilter(Filter):

    team_id = ForeignKeyFiltering(source='team', foreign_field='id')
    keyword = StringFiltering(source='title', lookup_type='regexp')
    day = DateCondition(source=Activity.start_time, function=fn.date)
    min_date = DateCondition(source=Activity.start_time, function=fn.date,
                             lookup_type='gte')
    max_date = DateCondition(source=Activity.start_time, function=fn.date,
                             lookup_type='lte')

    class Meta:
        fields = ('team_id', 'keyword', 'sport', 'lat', 'lng', 'day',
                  'min_date', 'max_date')


class ActivitySortFilter(SortFilter):

    # TODO: SortFilter 支持自定义的排序方法
    start_time = Filtering(source=Activity.start_time)
    end_time = Filtering(source=Activity.end_time)

    class Meta:
        # which fields maybe ordered
        fields = ('start_time',)

        # specifying default order
        ordering = ('-end_time',)


@rest_app.route(r'/activities', name='rest_activity_model')
class ActivityModelHandler(BaseClubAPIHandler, AMapMixin):

    filter_classes = (ActivitySearchFilter, ActivitySortFilter)

    def has_create_permission(self, team):
        """
        是否具有创建活动的权限
        Args:
            team: Team, 要创建活动的俱乐部

        Returns:

        """
        # TODO: 俱乐部管理者应该具有创建活动的权限
        if self.current_user == team.owner:
            return True
        raise ApiException(403, "没有创建活动的权限")

    def get(self):
        query = Activity.select(
            Activity,
            Sport,
        ).join(
            Sport, on=(Activity.sport == Sport.id).alias("sport")
        )

        query = self.filter_query(query)
        page = self.paginate_query(query)
        data = self.get_paginated_data(page, alias='activities',
                                       serializer=SimpleActivitySerializer)
        self.write(data)

    @validate_arguments_with(schemas.create_activity)
    @authenticated
    @gen.coroutine
    def post(self):
        form = self.validated_arguments
        team = Team.get(id=form.pop("team_id"))
        self.has_create_permission(team)

        fields = copy.copy(form)

        # 如果有地址信息, 获取 GPS 信息
        if "city" in form and "address" in form:
            logging.debug("有 `city` 和 `address` 开始调用远程接口获取 GPS 信息")
            geocode = yield self.get_geocode(city=form["city"],
                                             address=form["address"])
            logging.debug("获取到 geocode: {0}".format(geocode))
            if geocode.get("geocodes", []):
                location = geocode['geocodes'][0]['location'].split(",")
                fields["lat"] = location[1]
                fields["lng"] = location[0]
                fields["geohash "] = geohash.encode(float(location[1]),
                                                    float(location[0]))

        # TODO: 处理循环类型
        if "repeat_type" in form:
            if form["repeat_type"] == "week":
                fields["week_day"] = form["start_time"].weekday() + 1

            elif form["repeat_type"] == "month":
                fields["month_day"] = form["start_time"].day

        activity = Activity.create(team=team, creator=self.current_user,
                                   leader=self.current_user,
                                   **fields)
        self.set_status(201)
        self.write(ActivitySerializer(instance=activity).data)


@rest_app.route(r'/activities/(\d+)', name='rest_activity_object')
class ActivityObjectHandler(BaseClubAPIHandler):
    """
    活动 object handler
    """

    def has_patch_permission(self, activity):
        """
        是否具有又该活动的权限
        Args:
            activity:

        Returns: bool

        """
        # Fixme: 俱乐部管理员都可以修改活动
        if activity.creator == self.current_user:
            return True
        raise ApiException(403, '权限错误')

    def get(self, activity_id):
        """
        获取活动详情
        Args:
            activity_id: 活动 ID

        """
        activity = Activity.get_or_404(id=activity_id)
        serializer = ActivitySerializer(instance=activity)

        self.write(serializer.data)

    @validate_arguments_with(schemas.patch_activity)
    @authenticated
    def patch(self, activity_id):
        """
        修改活动信息
        Args:
            activity_id:

        Returns:

        """
        activity = Activity.get_or_404(id=activity_id)
        form = self.validated_arguments
        self.has_patch_permission(activity)
        Activity.update(**form).where(Activity.id == activity_id).execute()

        updated = Activity.get_or_404(id=activity_id)
        self.write(ActivitySerializer(updated).data)


@rest_app.route(r'/activities/(\d+)/join')
class ActivityJoinHandler(BaseClubAPIHandler):

    def handle_file(self, field_name, activity):
        """
        处理上传的文件, 上传到七牛
        Args:
            field_name:
            activity:

        Returns: key

        """
        to_bucket = self.settings['qiniu_file_bucket']

        to_key = "user:%s%s" % (self.current_user.id, time.time())
        to_key = 'user/{0}/{1}' \
            .format(self.current_user.id,
                    hashlib.md5(to_key.encode()).hexdigest())
        key = self.upload_file(field_name, to_bucket=to_bucket, to_key=to_key)

        return key

    def upload_file(self, field, to_bucket, to_key,
                    allow_ext=('jpg', 'jpeg', 'png', 'gif', 'webp')):

        upload_file = self.request.files.get(field)
        if not upload_file:
            raise ArgumentError(400, "没有上传")

        filename = upload_file[0]['filename']
        if not filename or filename.split(".")[-1].lower() not in allow_ext:
            raise ArgumentError(400, "上传格式不支持")

        ext = filename.split(".")[-1].lower()
        file_body = upload_file[0]['body']
        if not file_body:
            raise ArgumentError(400, "上传文件为空")

        # 最大5M
        elif len(file_body) > 5100000:
            raise ArgumentError(400, "上传文件不能超过5M")

        to_key = to_key + "." + ext
        ret, info = tasks.qiniu_tool.put_data(to_bucket, to_key,
                                              file_body,
                                              check_crc=True)
        if not ret:
            self.logger.debug("上传文件到七牛失败：%s" % info)
            raise ArgumentError(500, "保存失败，请稍后重试")

        return "%s:%s" % (to_bucket, to_key)

    def handle_extra_fields(self, activity):
        """
        处理自定义字段
        Args:
            activity: Activity instance

        Returns:

        """
        _types = {
            'info_ext1': activity.need_ext1_type,
            'info_ext2': activity.need_ext2_type,
            'info_ext3': activity.need_ext3_type
        }

        keys = {}
        for field_name, field_type in _types.items():
            if field_type == 'photo':
                keys[field_name] = self.handle_file(field_name, activity)
            else:
                keys[field_name] = self.get_argument(field_name, None)

        keys["mobile"] = self.validated_arguments.get("mobile",
                                                      self.current_user.mobile)
        keys.update({
            "gps_enabled": self.validated_arguments.get("gps_enabled", False),
            'nickname': self.validated_arguments["nickname"],
            'gender': self.validated_arguments["gender"],
            'realname': self.validated_arguments["name"],
            'identification': self.validated_arguments["identification"],
            'emergency_contact': self.validated_arguments["emergency_contact"],
        })
        return keys

    def handle_cash_pay(self, activity: Activity, form, extra_fields):
        member_state = ActivityMember.ActivityMemberState.confirmed.value
        total_fee = activity.price * form['users_count']

        if total_fee == 0:
            payment_state = TeamOrder.OrderState.TRADE_BUYER_PAID.value
        else:
            payment_state = TeamOrder.OrderState.WAIT_BUYER_PAY.value

        self.add_member_and_finish_request(activity=activity, order=None,
                                           total_fee=total_fee,
                                           member_state=member_state,
                                           payment_state=payment_state,
                                           form=form,
                                           extra_fields=extra_fields)

    def handle_online_pay(self, activity, form, extra_fields):
        member_state = ActivityMember.ActivityMemberState.wait_confirm.value
        total_fee = activity.price * form['users_count']

        if total_fee == 0:
            payment_state = TeamOrder.OrderState.TRADE_BUYER_PAID.value
        else:
            payment_state = TeamOrder.OrderState.WAIT_BUYER_PAY.value

        if total_fee > 0:
            order = TeamMemberService.new_order(
                team=activity.team,
                activity_id=activity.id,
                user=self.current_user,
                order_type=TeamOrder.OrderType.ACTIVITY.value,
                payment_method=form['payment'],
                total_fee=total_fee,
                payment_fee=total_fee,
                title=activity.title
            )
        else:
            order = None

        self.add_member_and_finish_request(activity=activity,
                                           order=order,
                                           total_fee=total_fee,
                                           member_state=member_state,
                                           payment_state=payment_state,
                                           form=form,
                                           extra_fields=extra_fields)

    def get_activity(self, activity_id) -> Activity:
        try:
            activity = Activity.get(id=activity_id)
        except Activity.DoesNotExist:
            raise ApiException(400, "活动不存在")
        return activity

    def validate_activity_visible(self, activity: Activity):
        """
        校验是否允许报名
        Args:
            activity:
        """
        if activity.visible == 0:
            # 所有人可加入
            return True
        else:
            team = activity.team
            if activity.allow_groups:
                # 特定组成员可加入
                team_member = Team.get_member(team_id=team.id,
                                              user_id=self.current_user.id)
                if team_member.group_name in activity.allow_groups:
                    return True
                else:
                    raise ApiException(403, "该活动之允许特定分组成员加入, "
                                            "你不是该组成员")
            if team.is_member(self.current_user.id):
                # 会员均可加入
                return True
            else:
                raise ApiException(403, "该活动仅允许会员参加, 你还不是该俱乐部会员")

    def validate_together(self, activity, form):
        """
        校验 activity
        """
        users_count = form['users_count']
        # 人数已满、活动已取消、活动已截止等无法报名
        can = activity.can_apply()
        if can is not True:
            raise ApiException(400, can)

        if users_count > activity.allow_agents + 1:
            raise ApiException(
                400, message='报名人数不能超过 %s' % (activity.allow_agents + 1))

        if users_count > (activity.max_members - activity.members_count):
            raise ApiException(
                400,
                message='该活动只有 %s 名额了' %
                        (activity.max_members - activity.members_count)
            )

        if Activity.is_member(activity.id, self.current_user.id):
            raise ApiException(400, message="你已报名此活动，不能重复报名")

    def sync_user_info(self, extra_fields):
        """ 同步报名信息到用户信息
        """

        update_user_attrs = {}
        if not self.current_user.name and extra_fields.get("nickname", None):
            update_user_attrs['name'] = extra_fields['nickname']

        if self.current_user.gender not in ('f', 'm') and \
                extra_fields.get("gender", None):
            update_user_attrs['gender'] = extra_fields['gender']

        if update_user_attrs:
            User.update(
                **update_user_attrs
            ).where(
                User.id == self.current_user.id
            ).execute()

    def auto_join_team(self, team):
        """ 自动加入俱乐部
        """

        if team.is_member(self.current_user.id):
            return

        if team.open_type == 3:
            # 不允许任何人加入
            return

        if team.open_type == 0:
            # 允许任何人加入
            member_state = TeamMember.TeamMemberState.normal
            team.add_member(self.current_user.id, state=member_state)
        elif team.open_type == 1:
            # 须要验证
            member_state = TeamMember.TeamMemberState.pending
            team.add_member(self.current_user.id, state=member_state)

    @validate_arguments_with(schemas.join_activity)
    @authenticated
    def post(self, activity_id):
        activity = self.get_activity(activity_id)
        form = self.validated_arguments
        extra_fields = self.handle_extra_fields(activity)

        self.validate_activity_visible(activity)

        self.validate_together(activity, form)

        if activity.payment_type == Activity.PaymentType.CASH_PAY.value:
            self.handle_cash_pay(activity=activity,
                                 form=form,
                                 extra_fields=extra_fields)
        else:
            self.handle_online_pay(activity=activity,
                                   form=form,
                                   extra_fields=extra_fields)

    def add_member_and_finish_request(self, activity, order, total_fee,
                                      member_state, payment_state, form,
                                      extra_fields):
        """
        Args:
            activity: 要参加的活动,
            order: 订单
            total_fee: 总金额,
            member_state: ActivityMember.state,
            payment_state: TeamOrder.state
            form:
            extra_fields: 参加活动的自定义字段
        """
        activity.add_member(
            user_id=self.current_user.id,
            users_count=form['users_count'],
            price=activity.price,
            free_times=0,
            total_fee=total_fee,
            order_id=order.id if order else 0,
            order_no=order.order_no if order else 0,
            payment_state=payment_state,
            state=member_state,
            **extra_fields,
        )

        self.sync_user_info(extra_fields)
        self.auto_join_team(activity.team)

        self.write_success(
            state=member_state,
            payment_state=TeamOrder.OrderState(payment_state).name,
            order_no=order.order_no if order else ""
        )


@rest_app.route(r"/activities/(\d+)/members")
class ActivityMembers(BaseClubAPIHandler):
    """活动报名成员列表"""

    def get_serializer(self, activity):
        if self.current_user == activity.creator:
            return InsecureActivityMemberSerializer
        return SecureActivityMemberSerializer

    def get(self, activity_id):
        activity = Activity.get(id=activity_id)
        query = ActivityMember.select()\
            .where(ActivityMember.activity == activity)
        query = self.filter_query(query)
        page = self.paginate_query(query)
        data = self.get_paginated_data(
            page=page,
            alias="members",
            serializer=self.get_serializer(activity)
        )
        self.write(data)


@rest_app.route(r"/activities/(\d+)/members/(\d+)")
class ActivityMemberDetailHandler(BaseClubAPIHandler):
    """会员报名资料"""

    def has_read_permission(self, activity):
        # Fixme: 俱乐部管理者都可以查看报名信息
        if activity.creator == self.current_user:
            return True
        raise ApiException(403, "无权查看会员报名资料")

    @authenticated
    def get(self, activity_id, member_id):
        activity = Activity.get_or_404(id=activity_id)
        self.has_read_permission(activity)

        member = ActivityMember.get_or_404(id=member_id)

        self.write(InsecureActivityMemberSerializer(member).data)


class MyActivitiesSerializer(Serializer):

    order_no = SerializerField(source='get_order_no')
    payment_state = SerializerField(source='get_payment_state')
    member = SecureActivityMemberSerializer(source='activity_member')
    order = OrderSimpleSerializer(source="order")

    class Meta:
        recurse = True

    def get_order_no(self):
        return self.instance.activity_member.order_no

    def get_payment_state(self):
        return self.instance.activity_member.payment_state


class MyActivitiesSearchFilter(Filter):

    day = DateCondition(source='start_time', lookup_type='regexp')

    class Meta:
        fields = ('day',)


@rest_app.route(r'/users/(\d+)/activities')
class MyActivities(BaseClubAPIHandler):
    """
    我参加的活动列表
    """

    filter_classes = (MyActivitiesSearchFilter,)

    def get(self, user_id):
        """
        按批次返回参加的活动
        """
        query = Activity.select(Activity, ActivityMember, TeamOrder)\
            .join(ActivityMember,
                  on=(ActivityMember.activity == Activity.id)
                  .alias('activity_member')) \
            .switch(Activity)\
            .join(
                TeamOrder,
                join_type=JOIN_LEFT_OUTER,
                on=(TeamOrder.id == ActivityMember.order_id).alias("order")
            ) \
            .where(ActivityMember.user == user_id)

        query = self.filter_query(query)
        page = self.paginate_query(query=query)
        data = self.get_paginated_data(page=page, alias='activities',
                                       serializer=MyActivitiesSerializer)

        self.write(data)


@rest_app.route(r'/activities/(\d+)/leave', name='rest_activity_leave')
class LeaveActivityHandler(BaseClubAPIHandler):
    """
    退出活动
    """

    @authenticated
    def get(self, activity_id, *args, **kwargs):

        activity = Activity.get_or_404(id=activity_id)

        if not Activity.is_member(activity.id, user_id=self.current_user):
            raise ApiException(400, '未参加活动, 不用退出')

        self.can_leave(activity)

        activity.leave(user=self.current_user)
        self.set_status(204)

    def can_leave(self, activity: Activity):
        """
        是否可以退出
         1. 状态为 opening
         2. 报名未截止
        """
        opening_state = Activity.ActivityState.opening.value
        if activity.state is opening_state and \
                (activity.join_end, activity.start_time)[True] > datetime.datetime.now():
            return True

        raise ApiException(400, "活动关闭或报名截止, 不能主动退出")


@rest_app.route(r"/users/(\d+)/activities/(\d+)/profile")
class ActivityProfile(BaseClubAPIHandler):
    """
    获取活动报名资料
    """

    def joined_this_activity(self, activity_id, user_id):
        """用户是否参加了对应活动"""
        try:
            member = ActivityMember.get(activity=activity_id,
                                        user=user_id)
        except ActivityMember.DoesNotExist:
            raise ApiException(400, "未参加该活动")

        return member

    def get_serializer(self, member: ActivityMember):
        """
        查看自己的资料或者活动管理者可以查看 Insecure 级别
        查看他人资料只能查看 Secure 级别
        """
        if self.current_user == member.user or \
                self.current_user == member.activity.creator:
            serializer = InsecureActivityMemberSerializer

        else:
            serializer = SecureActivityMemberSerializer
        return serializer

    @authenticated
    def get(self, user_id, activity_id):
        """
        获取活动报名资料
        """

        member = self.joined_this_activity(activity_id, user_id)
        serializer = self.get_serializer(member)

        self.write(serializer(instance=member).data)

    def handle_extra_fields(self, activity):
        """
        处理自定义字段
        Args:
            activity: Activity instance

        Returns:

        """
        _types = {
            'info_ext1': activity.need_ext1_type,
            'info_ext2': activity.need_ext2_type,
            'info_ext3': activity.need_ext3_type
        }

        fields = {}
        for field_name, field_type in _types.items():
            if field_name in self.request.arguments:
                if field_type == 'photo':
                    fields[field_name] = self.handle_file(field_name, activity)
                else:
                    fields[field_name] = self.get_argument(field_name)

        return fields

    def handler_required_fields(self, activity):
        expect_fields = {
            "nickname": activity.need_nickname,
            "mobile": activity.need_mobile,
            "realname": activity.need_name,
            "gender": activity.need_gender,
            "gps_enabled": activity.need_gps,
            "identification": activity.need_identification,
            "emergency_contact": activity.need_emergency_contact
        }

        fields = {}
        for field_name, required in expect_fields.items():
            if required is True and (field_name in self.validated_arguments):
                field_value = self.validated_arguments[field_name]
                if not field_value:
                    raise "{field} 为必填项, 不能为空".format(field=field_name)
                fields[field_name] = field_value
        return fields

    @validate_arguments_with(schemas.patch_member_profile)
    @authenticated
    def patch(self, user_id, activity_id):
        """
        修改报名信息
        """
        try:
            activity = Activity.get(id=activity_id)
        except Activity.DoesNotExist:
            raise ApiException(404, "活动不存在")

        self.joined_this_activity(activity_id, user_id)

        # 校验提交的参数是否合法, 1. 自定义参数; 2. 必填参数是否发生修改
        fields = {}
        fields.update(self.handle_extra_fields(activity=activity))
        fields.update(self.handler_required_fields(activity))

        if not fields:
            raise ApiException(400, "填写需要修改的属性和值")

        ActivityMember.update(**fields)\
            .where(ActivityMember.activity == activity_id,
                   ActivityMember.user == user_id)\
            .execute()

        self.set_status(204)
