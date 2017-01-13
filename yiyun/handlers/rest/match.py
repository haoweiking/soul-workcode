from typing import Set, Dict
import logging
import hashlib
import time
import json
from datetime import datetime
from urllib.parse import urljoin
from copy import copy

from peewee import prefetch

from peewee import JOIN_LEFT_OUTER
from yiyun.tasks import match_notify
from yiyun.helpers import create_token, Storage, is_mobile, intval
from yiyun.libs.parteam import Parteam, ParteamUser
from yiyun.libs.pagination import Page, Paginator
from yiyun.libs.algorithms import latitude_calculator
from yiyun.models import (User, Team, Match, fn, MatchMember, MatchOption,
                          MatchStatus, MatchGroup, MatchCover, MatchRound,
                          MatchAgainst, TeamOrder, MatchComment, TeamMember,
                          MatchStatusLike)
from yiyun.exceptions import ArgumentError
from yiyun.service.match import (MatchStatusService, MatchService,
                                 MatchException)
from yiyun.service.user import UserService
from .base import (rest_app, BaseClubAPIHandler, authenticated,
                   validate_arguments_with, ApiException, )
from .serializers.match import (MatchSerializer, SimpleMatchSerializer,
                                MatchStatusSerializer, MatchCommentSerializer,
                                MatchStatusSimpleSerializer)
from .serializers.team import MiniTeamSerializer
from .filter.match import MatchCommentSortFilter, MatchSearchFilter
from .schemas import match as schemas


@rest_app.route(r'/matches')
class MatchsHandler(BaseClubAPIHandler):

    def get(self):
        """ 获取赛事列表
        """

        team_id = self.get_argument("team_id", None)
        keyword = self.get_argument("keyword", None)
        sport = self.get_argument("sport", None)
        province = self.get_argument("province", None)
        city = self.get_argument("city", None)
        sort = self.get_argument("sort", 'newest')

        query = Match.select(
            Match,
            Team,
        ).join(
            Team, on=(Team.id == Match.team_id).alias("team")
        ).where(
            Match.state << (Match.MatchState.opening,
                            Match.MatchState.finished)
        )

        if team_id:
            query = query.where(Match.team_id == team_id)

        if keyword:
            query = query.where(Match.title.contains(keyword))

        if sport:
            sport = sport.split(",")
            query = query.where(Match.sport_id << sport)

        if province:
            province = province.split(",")
            query = query.where(Match.province << province)

        if city:
            city = city.split(",")
            query = query.where(Match.city << city)

        if sort == 'newest':
            # 未结束的
            query = query.where(Match.end_time >= datetime.now())

            # 按开始时间排序
            query = query.order_by("start_time")

        elif sort == 'hottest':
            # 未结束的
            query = query.where(Match.end_time >= datetime.now())

            # 按报名要数排序
            query = query.order_by("-members_count")

        elif sort == 'colsest':
            # 已结束的
            query = query.where(Match.end_time <= datetime.now())

            # 按结束时间倒序
            query = query.order_by("-end_time")
        if sort == "distance":
            lat = self.get_query_argument("lat", None)
            lon = self.get_query_argument("lng", None)
            distance = intval(self.get_query_argument("distance", 10))
            if distance > 100:
                distance = 100
            if distance < 1:
                distance = 1

            if not (lat and lon):
                raise ApiException(400, "按距离排序需要提供经纬值")
            lat, lon = float(lat), float(lon)
            min_lat, min_lon, max_lat, max_lon = \
                self.calculate_range(distance, lat, lon)
            tmp_query = query.where(Match.lat.between(min_lat, max_lat),
                                    Match.lng.between(min_lon, max_lon))
            sorted_matches = self.sorting_by_distance(tmp_query, lat, lon)
            data = self.render_page_info(self.paginate_query(tmp_query))
            paged = self.paged_data(sorted_matches)
            data["matches"] = [SimpleMatchSerializer(row).data for row in
                               paged]
        else:
            page = self.paginate_query(query)

            data = self.get_paginated_data(page=page,
                                           alias='matches',
                                           serializer=SimpleMatchSerializer)
        self.write(data)

    def paged_data(self, li: list):
        """
        按照分页获取 list
        :param li:
        :return: [Match,]
        """
        limit = self.get_query_argument("limit", 20)
        try:
            limit = int(limit)
        except TypeError:
            limit = 20
        page = self.get_query_argument("page", 1)
        try:
            page = int(page)
        except TypeError:
            page = 1

        start_index = (page - 1) * limit
        paged = li[start_index: start_index + limit]
        return paged

    def sorting_by_distance(self, query, lat, lon):
        """
        按照距离排序
        :param query:
        :param lat:
        :param lon:
        :return:
        """
        matches = [row for row in query]  # type: List[Match]

        for match in matches:
            dist = latitude_calculator(lat, lon, match.lat, match.lng)
            setattr(match, "_distance", dist)
        return sorted(matches, key=lambda x: x._distance)

    def calculate_range(self, distance, my_lat: float, my_lon: float):
        """
        计算对应搜索距离的最大最小经纬度
        :return (min_location, max_location)
        """
        import math
        range = 180 / math.pi * distance / 6372.797
        lon_range = range / math.cos(my_lat * math.pi / 180.0)
        max_lat = my_lat + range
        min_lat = my_lat - range
        max_lon = my_lon + lon_range
        min_lon = my_lon - lon_range
        return min_lat, min_lon, max_lat, max_lon


@rest_app.route(r"/matches/(\d+)", name="rest_match")
class MatchHandler(BaseClubAPIHandler):

    """单个赛事接口"""

    def get_object(self, match_id: int, preview: bool =False):
        try:
            if preview:
                query = Match.select().where(Match.id == match_id)
            else:
                query = Match.select()\
                    .where(Match.id == match_id,
                           (Match.state == Match.MatchState.closed.value) |
                           (Match.state == Match.MatchState.cancelled.value) |
                           (Match.state == Match.MatchState.opening.value) |
                           (Match.state == Match.MatchState.finished.value))
            obj = query.get()
        except Match.DoesNotExist:
            raise ApiException(404, "赛事不存在")
        return obj

    def get(self, match_id):
        """获取赛事信息

        :match_id: 赛事ID
        :returns: 赛事信息

        """

        preview = self.get_query_argument("preview", False)
        match = self.get_object(match_id, preview)
        match.team = Team.get_or_404(id=match.team_id)

        serializer = MatchSerializer(instance=match)

        info = serializer.data

        # 获取赛事分组信息
        query = MatchGroup.select().where(
            MatchGroup.match_id == match.id,
        ).order_by(
            MatchGroup.sort_num.desc()
        )

        groups = []
        for group in query:
            groups.append(group.info)

        info['groups'] = groups

        # 获取赛事海报列表
        query = MatchCover.select().where(
            MatchCover.match_id == match.id
        ).order_by(
            MatchCover.id.desc()
        )

        covers = []
        for cover in query:
            covers.append(cover.info)

        info['covers'] = covers

        if self.current_user:
            member = MatchMember.get_or_none(
                match_id=match_id,
                user_id=self.current_user.id
            )

            if member:
                info['my_state'] = member.mini_info

        self.write(info)


@rest_app.route(r"/matches/(\d+)/apply_form", name="rest_match_apply_form")
class MatchAppleFormHandler(BaseClubAPIHandler):

    """赛事报名表单"""

    def get(self, match_id):
        """获取赛事信息

        :match_id: 赛事ID
        :returns: 赛事信息

        """

        match = Match.get_or_404(id=match_id)

        # 获取自定义选项
        query = MatchOption.select().where(
            MatchOption.match_id == match.id
        ).order_by(
            MatchOption.sort_num.desc()
        )

        options = []
        for option in query:
            options.append(option.info)

        self.write({
            "options": match.fields,
            "custom_options": options
        })


@rest_app.route(r"/matches/(\d+)/rounds", name="rest_match_rounds")
class MatchRoundsHandler(BaseClubAPIHandler):

    def get(self, match_id):
        """ 获取赛事轮次列表
        """

        match = Match.get_or_404(id=match_id)

        query = MatchRound.select().where(
            MatchRound.match_id == match.id
        ).order_by(
            MatchRound.start_time.asc()
        )

        rounds = []
        for match_round in query:
            rounds.append(match_round.info)

        RightMember = MatchMember.alias()

        against_query = MatchAgainst.select(
            MatchAgainst,
            MatchMember,
            RightMember
        ).join(
            MatchMember, on=(MatchAgainst.left_member_id == MatchMember.id).alias("left_member")
        ).switch(
            MatchAgainst
        ).join(
            RightMember,
            join_type=JOIN_LEFT_OUTER,
            on=(MatchAgainst.right_member_id == RightMember.id).alias("right_member")
        ).where(
            MatchAgainst.match_id == match_id
        ).order_by(
            MatchAgainst.start_time.asc()
        )

        againsts = {}
        for against in against_query:
            if against.round_id not in againsts:
                againsts[against.round_id] = []

            against_info = against.info
            against_info['left_member'] = against.left_member.mini_info

            if against.right_member:
                against_info['right_member'] = against.right_member.mini_info

            againsts[against.round_id].append(against_info)

        for i in range(0, len(rounds)):
            round_id = rounds[i]['id']
            rounds[i]['against_mapping'] = againsts.get(round_id, [])

        self.write({
            "rounds": rounds
        })


@rest_app.route(r"/matches/(\d+)/join", name="rest_match_join")
class JoinMatchHandler(BaseClubAPIHandler):

    def parse_options(self, match_id):

        # 获取自定义选项
        query = MatchOption.select().where(
            MatchOption.match_id == match_id
        ).order_by(
            MatchOption.sort_num.desc()
        )

        option_values = []
        for option in query:
            is_photo = False

            if option.field_type in ("photo", "file"):
                is_photo = True
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "match:%s%s" % (match_id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                try:
                    value = self.upload_file("option_{0}".format(option.id),
                                             to_bucket=to_bucket,
                                             to_key=to_key,
                                             required=option.required
                                             )
                except ArgumentError as e:
                    raise ApiException(400, "{0}{1}".format(option.title, e.message))

            else:
                value = self.get_argument("option_{0}".format(option.id), None)
                if option.required and not value:
                    raise ApiException(400, "{0}必填".format(option.title))

                elif option.field_type in ("choice",) and \
                        value not in option.choices.replace("｜", "|").split("|"):

                    raise ApiException(400, "{0}选择错误".format(option.title))

                elif option.field_type in ("choice",):
                    choices = set(option.choices.replace("｜", "|").split("|"))
                    value = set(value.split("|"))

                    if len(choices & value) == 0:
                        raise ApiException(400, "{0}选择错误".format(option.title))

                    value = "|".join(value)

            option_values.append({
                "option_id": option.id,
                "option_title": option.title,
                "value": value,
                "is_photo": is_photo
            })

        return option_values

    def upload_photo(self, field_name, field_title, required=False):

        to_bucket = self.settings['qiniu_avatar_bucket']
        to_key = "match:%s%s" % (create_token(8), time.time())
        to_key = hashlib.md5(to_key.encode()).hexdigest()

        try:
            file_key = self.upload_file(field_name,
                                        to_bucket=to_bucket,
                                        to_key=to_key,
                                        )
        except ArgumentError as e:
            if required:
                raise ApiException(400, "{0}{1}".format(field_title, e.message))
            else:
                file_key = ""

        return file_key

    def has_joined(self, match: Match, user_id: int):
        """
        用户是否已经加入过赛事
        :param match:
        :param user_id:
        :return:
        """
        try:
            member = MatchMember.select()\
                .where(MatchMember.user_id == user_id,
                       MatchMember.match_id == match.id)\
                .get()
        except MatchMember.DoesNotExist:
            return True
        else:
            if member.state == MatchMember.MatchMemberState.leave.value:
                msg = "你的退赛申请正在处理中, 退赛完成后再尝试"
                raise ApiException(422, msg, log_message=msg)
            raise ApiException(422, "您已参赛, 无须重复参加")

    @authenticated
    def post(self, match_id):
        """ 报名赛事

        :match_id: 赛事ID
        :returns:

        """

        match = Match.get_or_404(id=match_id)

        # 检查赛事是否可以报名
        result = match.can_join()
        self.has_joined(match, user_id=self.current_user.id)

        if not result['can']:
            raise ApiException(403, result['reason'],
                               log_message="报名失败：{0}, {1}".format(match_id, result['reason']))

        team = Team.get_or_404(id=match.team_id)

        # 分组比赛模式
        group = None
        if match.group_type == 1:
            group_id = self.get_argument("group_id")
            group = MatchGroup.get_or_none(
                id=group_id,
                match_id=match_id
            )
            if group is None:
                raise ApiException(404, "赛事分组不存在")

            # 分组是否已报满
            if group.max_members <= group.members_count:
                raise ApiException(403, "赛事分组已报满")

            total_fee = group.price

        else:
            total_fee = match.price

        name = self.get_argument("name")
        mobile = self.get_argument("mobile")

        if not name:
            raise ApiException(400, "请填写名称")

        if not mobile:
            raise ApiException(400, "请填写手机号码")

        elif not is_mobile(mobile):
            raise ApiException(400, "手机号码格式有误")

        # TODO: 上线前移除
        # member = MatchMember.get_or_none(match_id=match.id,
        #                                  user_id=self.current_user.id)
        # if member is not None:
        #     raise ApiException(403, "你已报名此赛事，无需重复报名")

        extra_attrs = self.parse_options(match_id)

        with self.db.transaction() as txn:

            # 零元赛事无需支付不生成订单
            order = None
            if total_fee > 0:
                order = TeamOrder.create(order_no=TeamOrder.get_new_order_no(),
                                         team=team,
                                         user=team.owner_id,
                                         title=match.title,
                                         order_type=TeamOrder.OrderType.MATCH,
                                         payment_fee=total_fee,
                                         total_fee=total_fee,
                                         activity_id=match.id,
                                         state=TeamOrder.OrderState.WAIT_BUYER_PAY
                                         )

            other_attrs = {}
            if "avatar" in match.fields:
                other_attrs['avatar_key'] = self.upload_photo("avatar", "头像")

            if "idcard_photo" in match.fields:
                other_attrs['idcard_front'] = self.upload_photo("idcard_front", "证件照片正面")
                other_attrs['idcard_back'] = self.upload_photo("idcard_back", "证件照片背面")

            gender = self.get_argument("gender", "")
            if gender in ("0", "1"):
                gender = ("f", "m")[int(gender)]
            else:
                gender = "n"

            if order and order.state == TeamOrder.OrderState.WAIT_BUYER_PAY:
                member_state = MatchMember.MatchMemberState.wait_pay
            else:
                member_state = MatchMember.MatchMemberState.normal

            team.add_member(self.current_user.id, nick=name,
                            state=TeamMember.TeamMemberState.normal)
            member = MatchMember.create(
                match_id=match.id,
                group_id=group.id if group else 0,
                member_type=match.join_type,
                user_id=self.current_user.id,
                name=name,
                mobile=mobile,
                gender=gender,
                age=self.get_argument("age", "0"),
                is_leader=self.get_argument("is_leader", False),
                realname=self.get_argument("realname", ""),
                idcard_number=self.get_argument("idcard_number", ""),
                extra_attrs=extra_attrs,
                order_id=order.id if order else 0,
                total_fee=total_fee,
                state=member_state,
                **other_attrs
            )

            # 如果需要付费则生成支付订单
            if total_fee > 0:

                if match.refund_expire:
                    refund_expire = match.refund_expire.strftime("%Y%m%d%H%M%S")
                else:
                    refund_expire = datetime.now().strftime("%Y%m%d%H%M%S")

                resp = self.parteam_request("/match/openapi/createOrderInfo.do", post_args={
                    "orderValue": match.id,
                    "eachFee": int(total_fee * 100),
                    "num": 1,
                    "totalFee": int(total_fee * 100),
                    "subject": match.title,
                    "userId": self.current_user.id,
                    "notifyUrl": urljoin(self.request.full_url(),
                                         self.reverse_url('rest_match_join_notify', match.id)),
                    "version": 1,
                    "expDatetime": refund_expire,
                    "tradeType": "APP" if self.device_type.lower() in ("ios", "android") else "WEB",
                })

                if "orderNo" not in resp:
                    txn.rollback()
                    raise ApiException(400, "创建订单失败",
                                       log_message="match order fail:{0}".format(resp))

                MatchMember.update(
                    pt_order_no=resp['orderNo']
                ).where(
                    MatchMember.id == member.id
                ).execute()

            # 统计赛事人数
            Match.update_members_count(match.id)
            if group:
                MatchGroup.update_members_count(group.id)

            member = MatchMember.get_or_404(id=member.id)

        member_info = member.info
        member_info['order'] = {
            "orderNo": member.pt_order_no,
            "orderValue": match.id,
            "eachFee": int(total_fee * 100),
            "num": 1,
            "totalFee": int(total_fee * 100),
            "subject": match.title,
            "userId": self.current_user.id,
        }

        self.write(member_info)


@rest_app.route(r"/matches/(\d+)/join/notify", name="rest_match_join_notify")
class JoinMatchNotifyHandler(BaseClubAPIHandler):

    verify_sign = False

    def post(self, match_id):
        """"
        TODO: 如果回调时赛事已满员则自动退款处理

        Parteam Api request example: {
          "message": "成功",
          "code": 200,
          "attribute": {
              "userId": 169,
              "orderNo": "11354642167546",
              "paymentMethod":1, // 支付类型 1微信，2支付宝
              "orderState":2 // // 订单状态 1 待付款 2 已付款 3 超时未付款 4 已发货
          }
        }
        """
        data = self.request.body.decode()
        data = json.loads(data)

        if not data.get("attribute"):
            raise ApiException(400, "未包含 attribute")

        order = data['attribute']
        member = MatchMember.get_or_404(pt_order_no=order['orderNo'])

        if order['orderState'] in (2, 4):

            # 将状态为未支付报名状态修改为正常
            if member.state == MatchMember.MatchMemberState.wait_pay:

                payment_method = (TeamOrder.OrderPaymentMethod.WXPAY,
                                  TeamOrder.OrderPaymentMethod.ALIPAY
                                  )[order['paymentMethod'] - 1]

                with self.db.transaction():
                    MatchMember.update(
                        state=MatchMember.MatchMemberState.normal
                    ).where(
                        MatchMember.id == member.id
                    ).execute()

                    TeamOrder.update(
                        paid=datetime.now(),
                        state=TeamOrder.OrderState.TRADE_BUYER_PAID,
                        gateway_trade_no=order['orderNo'],
                        payment_method=payment_method
                    ).where(
                        TeamOrder.id == member.order_id
                    ).execute()

                # 统计赛事人数
                Match.update_members_count(member.match_id)
                if member.group_id > 0:
                    MatchGroup.update_members_count(member.group_id)

            match_notify.join_match_done\
                .apply_async(args=[match_id, member.id], retry=True)

        self.write_success()


@rest_app.route(r"/matches/(\d+)/my_state", name="rest_match_my_state")
class MatchMyStateHandler(BaseClubAPIHandler):

    @authenticated
    def get(self, match_id):
        """ 我的状态
        """

        member = MatchMember.get_or_none(
            match_id=match_id,
            user_id=self.current_user.id
        )

        self.write(member.info)


@rest_app.route(r"/matches/(\d+)/leave", name="rest_match_leave")
class LeaveMatchHandler(BaseClubAPIHandler):
    """
    退出赛事
    """

    def can_leave(self, match: Match, user_id: int) -> bool:
        """
        赛事是否可以退出
        :param match:
        :param user_id:
        :return:
        """

        # 先判断是否加入过赛事
        self.has_joined_match(match, user_id)

        # 当前赛事状态是不是允许退出
        if match.can_leave():
            return True
        raise ApiException(422, "不满足赛事退塞条件, 无法退出")

    def has_joined_match(self, match, user_id) -> MatchMember:
        """
        用户是否加入赛事
        :param match:
        :param user_id:
        :return:
        """
        try:
            return MatchMember.get(user_id=user_id, match_id=match.id)
        except MatchMember.DoesNotExist:
            raise ApiException(422, "未加入赛事, 无须退出")

    @validate_arguments_with(schemas.leave_match)
    @authenticated
    def post(self, match_id: int):
        """
        提交退塞请求,
        http_form:
            reason: 退赛原因,
            insists: 强制退出, 强制退出比赛无退款
        :param match_id: int, Match.id
        """
        form = self.validated_arguments

        insists = form.pop("insists", False)
        match = Match.get_or_404(id=match_id)
        if not insists:
            self.can_leave(match, self.current_user.id)
        member = self.has_joined_match(match, user_id=self.current_user.id)

        notify_url = urljoin(self.request.full_url(),
                             self.reverse_url("rest_matches_refund_callback"))
        try:
            MatchService.leave(user_id=self.current_user.id, match=match,
                               notify_url=notify_url, insists=insists)
        except MatchException as e:
            logging.error(e)
            msg = "退出赛事失败, 原因: `{0}`".format(str(e))
            raise ApiException(422, msg)
        self.set_status(204, "退出赛事成功")
        self.finish()

        # user_info = {"mobile": member.mobile, "userId": member.user_id}
        # match_notify.match_refund.delay(match_id=member.match_id,
        #                                 order_no=member.pt_order_no,
        #                                 user_info=user_info)


@rest_app.route(r"/matches/refund/callback",
                name="rest_matches_refund_callback")
class LeaveMatchCallbackHandler(BaseClubAPIHandler):
    """
    退出赛事后, 派队退款操作的回调地址
    """

    # login_required = False
    verify_sign = False

    def parse_body(self):
        body = json.loads(self.request.body.decode())
        return body

    # def post(self):
    #     """
    #     退款回调接口
    #     :return:
    #     """
    #     body = self.parse_body()
    #     usefully = body["attribute"]
    #     pt_order_no = usefully["orderNo"]
    #     # refund_fee = usefully["refundFee"]
    #
    #     try:
    #         member = MatchMember.select()\
    #             .where(MatchMember.pt_order_no == pt_order_no,
    #                    MatchMember.state == MatchMember.MatchMemberState.leave.value)\
    #             .get()
    #     except MatchMember.DoesNotExist as e:
    #         logging.error("需要处理的赛事成员记录不存在")
    #         raise ApiException(400, str(e))
    #
    #     match = Match.get(id=member.match_id)
    #     with self.db.transaction():
    #         MatchService.leave(user_id=member.user_id, match=match,
    #                            insists=True)
    #         TeamOrder.update(state=TeamOrder.OrderState.TRADE_CLOSED.value,
    #                          refunded_fee=TeamOrder.payment_fee,
    #                          refund_state=TeamOrder.OrderRefundState.FULL_REFUNDING.value,
    #                          refunded_time=datetime.now())\
    #             .where(TeamOrder.id == member.order_id,
    #                    TeamOrder.state >= TeamOrder.OrderState.TRADE_BUYER_PAID.value)\
    #             .execute()
    #
    #     user_info = {"mobile": member.mobile, "userId": member.user_id}
    #     match_notify.match_refund.delay(match_id=member.match_id,
    #                                     order_no=pt_order_no,
    #                                     user_info=user_info)
    #     self.write_success()

    def post(self):
        """退款已采用同步回调, 此接口过期"""
        logging.warning("调用派队退款申请已采用同步回调的方式, 此接口已过期")
        self.write_success()


@rest_app.route(r"/matches/(\d+)/members", name="rest_match_members")
class MatchMembersHandler(BaseClubAPIHandler):

    def get(self, match_id):
        """ 获取赛事成员列表

        :match_id: 赛事ID
        :returns: TODO

        """
        match = Match.get_or_404(id=match_id)
        query = MatchService.members(match=match)

        filtered = self.filter_query(query)
        page = self.paginate_query(filtered)

        uids = self.get_parteam_uid(page)
        parteam_users = self.get_parteam_users(uids) if uids else {}

        data = self.render_page_info(page)
        data["members"] = self.serializing_members(page, parteam_users)

        self.write(data)

    def serializing_members(self, page, parteam_user: Dict[int, ParteamUser]):
        """输出 members 信息"""
        members = []
        for member in page:
            info = member.info
            info["user"] = parteam_user[member.user_id].secure_info
            members.append(info)
        return members

    def get_parteam_users(self, uids: Set[int]) -> Dict[int, ParteamUser]:
        """获取派队用户"""
        pt = Parteam(self.settings["parteam_api_url"])
        return pt.parteam_user(user_ids=list(uids))

    def get_parteam_uid(self, page) -> Set[int]:
        """获取 user_id"""
        uids = set()
        for row in page:
            uids.add(row.user_id)
        return uids


@rest_app.route(r"/matches/(\d+)/status", name="rest_match_status")
class MatchStatusesHandler(BaseClubAPIHandler):

    def get(self, match_id):
        """ 获取赛事动态列表
        """

        # 显示最近 n 条评论
        comments_count = self.get_query_argument("comments_count", 2)
        # 显示最近 n 个点赞
        likes_count = self.get_query_argument("likes_count", 5)

        query = MatchStatus.select()\
            .where(MatchStatus.match_id == match_id)\
            .order_by(MatchStatus.created.desc(), MatchStatus.id.desc())

        CommentAlias = MatchComment.alias()  # type: MatchComment
        subquery = CommentAlias.select(fn.COUNT(CommentAlias.id))\
            .where(CommentAlias.status == MatchComment.status,
                   CommentAlias.id >= MatchComment.id)
        comments = MatchComment.select().where(subquery <= comments_count)\
            .order_by(MatchComment.created.desc(), MatchComment.id.desc())

        likes = MatchStatusLike\
            .select(MatchStatusLike.status, MatchStatusLike.user_id)\
            .order_by(-MatchStatusLike.create_at, -MatchStatusLike.id)\
            .limit(likes_count)\
            .distinct()

        status_with_comments = prefetch(query, comments, likes)

        page = self.paginate_query(status_with_comments)

        _uids = set()
        for row in page:
            for like in row.likes_prefetch:
                _uids.add(like.user_id)
            for comments in row.comments_prefetch:
                _uids.add(comments.user_id)

        parteam_users = dict()
        if _uids:
            pt = Parteam(self.settings["parteam_api_url"])
            parteam_users = pt.parteam_user(list(_uids))

        serializer_kwargs = {"parteam_users": parteam_users}

        data = self.get_paginated_data(page=page, alias="match_status",
                                       serializer=MatchStatusSerializer,
                                       serializer_kwargs=serializer_kwargs)
        self.write(data)


@rest_app.route(r"/match_status/(\d+)", name="rest_match_status_show")
class MatchStatusObjectHandler(BaseClubAPIHandler):
    """
    赛事动态 (战报) 详情
    """

    def get(self, match_status_id):
        match_status = MatchStatus.get_or_404(id=match_status_id)

        # 显示最近 n 条评论
        comments_count = self.get_query_argument("comments_count", 2)
        # 显示最近 n 个点赞
        likes_count = self.get_query_argument("likes_count", 5)

        comments = MatchComment.select()\
            .where(MatchComment.status == match_status_id)\
            .order_by(-MatchComment.created, -MatchComment.id)\
            .limit(comments_count)

        likes = MatchStatusLike\
            .select(MatchStatusLike.status, MatchStatusLike.user_id)\
            .where(MatchStatusLike.status == match_status_id)\
            .order_by(-MatchStatusLike.create_at, -MatchStatusLike.id)\
            .limit(likes_count)\
            .distinct()

        setattr(match_status, "comments_prefetch", comments)
        setattr(match_status, "likes_prefetch", likes)

        _uids = set()
        for like in likes:
            _uids.add(like.user_id)
        for comments in comments:
            _uids.add(comments.user_id)

        parteam_users = dict()
        if _uids:
            pt = Parteam(self.settings["parteam_api_url"])
            parteam_users = pt.parteam_user(list(_uids))

        serializer = MatchStatusSerializer(match_status,
                                           parteam_users=parteam_users)
        self.write(serializer.data)


@rest_app.route(r"/match_status/(\d+)/comments",
                name="rest_match_status_comments")
class MatchStatusCommentsHandler(BaseClubAPIHandler):
    """
    赛事动态(战报)评论
    """

    filter_classes = (MatchCommentSortFilter,)

    def get(self, match_status_id):
        query = MatchComment.select()\
            .where(MatchComment.status == match_status_id)
        filtered_query = self.filter_query(query)
        page = self.paginate_query(filtered_query)

        _uids = set()
        for row in page:
            _uids.add(row.user_id)
            if row.reply_to_user_id > 0:
                _uids.add(row.reply_to_user_id)

        parteam_users = dict()
        if _uids:
            pt = Parteam(self.settings["parteam_api_url"])
            parteam_users = pt.parteam_user(list(_uids))

        data = self.get_paginated_data(
            page, alias="comments", serializer=MatchCommentSerializer,
            serializer_kwargs={"parteam_users": parteam_users})
        self.write(data)

    @validate_arguments_with(schemas.new_match_comment)
    @authenticated
    def post(self, match_status_id):
        form = self.validated_arguments
        match_status = MatchStatus.get_or_404(id=match_status_id)
        inst = MatchComment.create(user_id=self.current_user.id,
                                   status=match_status,
                                   match=match_status.match_id,
                                   **form)

        self.set_status(201, reason="提交评论成功")

        if isinstance(self.current_user, Storage):
            parteam_users = {self.current_user.id: ParteamUser(self.current_user)}
        else:
            parteam_users = {}

        self.write(MatchCommentSerializer(inst, parteam_users=parteam_users).data)


@rest_app.route(r"/match_status/(\d+)/likes", name="rest_match_status_like")
class MatchStatusLikeHandler(BaseClubAPIHandler):
    """
    赛事动态点赞和获取点赞列表
    """

    def get(self, match_status_id):
        match_status = MatchStatus.get_or_404(id=match_status_id)
        query = MatchStatusService.get_likes(match_status)
        page = self.paginate_query(query)

        data = self.render_page_info(page)

        users = set([like.user_id for like in page])
        likes = []
        if users:
            parteam = Parteam(self.settings["parteam_api_url"])
            users = parteam.parteam_user(list(users))
            likes = [users[uid].secure_info for uid in users
                     if uid in users.keys()]
        data.update({"likes": likes})
        self.write(data)

    @authenticated
    def post(self, match_status_id):
        match_status = MatchStatus.get_or_404(id=match_status_id)
        liked = MatchStatusService.do_like(user_id=self.current_user.id,
                                           match_status=match_status)
        self.set_status(204, reason="点赞成功")
        # self.write(MatchStatusSimpleSerializer(liked).data)

    @authenticated
    def delete(self, match_status_id):
        """
        用户取消点赞,
        该方法会取消当前登录用户对本动态的所有点赞
        :param match_status_id:
        :return:
        """
        match_status = MatchStatus.get_or_404(id=match_status_id)
        status = MatchStatusService.undo_like(user_id=self.current_user.id,
                                              match_status=match_status)
        self.write(MatchStatusSimpleSerializer(status).data)


@rest_app.route(r"/users/(\d+)/matches", name="rest_user_matches")
class UserMatchesHandler(BaseClubAPIHandler):

    filter_classes = (MatchSearchFilter,)

    def get_paginated_data(self, page: Page, alias, **kwargs) -> dict:
        """
        获取分页后的数据
        Args:
            page: Page,
            alias:
            serializer
            serializer_kwargs:

        Returns: dict()
            num_pages: int, 总页数,
            previous_page: int, 上一页
            current_page: int, 当前页码
            next_pate: int, 下一页
            total: 总数
            per_page: 每页返回数
            results: list, 查询结果

        """
        data = self.render_page_info(page)

        if page:
            data[alias] = []
            for row in page:
                info = row.list_info
                info['team'] = row.team.mini_info
                info['my_state'] = row.member.mini_info
                data[alias].append(info)

        else:
            data[alias] = []

        data.update(kwargs)

        return data

    def get(self, user_id):
        """ 获取用户参与的比赛
        """

        paid = self.get_argument("paid", None)

        query = Match.select(
            Match,
            MatchMember,
            Team
        ).join(
            MatchMember, on=(MatchMember.match_id == Match.id).alias("member")
        ).switch(Match).join(
            Team, on=(Match.team_id == Team.id).alias("team")
        ).where(
            MatchMember.user_id == user_id
        )

        if paid == "0":
            query = query.where(MatchMember.state ==
                                MatchMember.MatchMemberState.wait_pay)
        elif paid == "1":
            query = query.where(MatchMember.state >
                                MatchMember.MatchMemberState.wait_pay)

        query = self.paginate_query(query)
        filtered = self.filter_query(query)
        page = self.paginate_query(filtered)

        data = self.get_paginated_data(page=page,
                                       alias='matches')

        self.write(data)


@rest_app.route(r"/users/(\d+)/following_teams")
class UserFollowerTeamHandler(BaseClubAPIHandler):
    """用户关注的俱乐部"""

    def get(self, user_id: int):
        query = UserService.following_teams(user_id=user_id)
        page = self.paginate_query(query)
        data = self.get_paginated_data(page, alias="teams",
                                       serializer=MiniTeamSerializer)
        self.write(data)
