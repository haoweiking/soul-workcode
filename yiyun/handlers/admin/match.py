import hashlib
import time
from datetime import datetime
from functools import reduce

import tornado.escape
import tornado.gen
import tornado.web
from peewee import JOIN_LEFT_OUTER, fn
from wtforms import ValidationError

from yiyun import service
from yiyun.exceptions import ArgumentError
from yiyun.helpers import intval, decimalval
from yiyun.models import (User, Team, Match, Sport,
                          ChinaCity, MatchRound,
                          MatchStatus, MatchMember, MatchOption,
                          MatchGroup, MatchCover, MatchAgainst,
                          SettlementApplication)
from yiyun.service.match import MatchService
from .base import AdminBaseHandler, admin_app
from .forms.match import (CreateRoundForm, EditRoundForm,
                          CreateCoverForm, MatchStatusForm, EditMatchFrom)


class MatchStatusHandlerMixin(object):

    def upload_photos(self, match_id):
        photo_keys_list = []
        for file in self.request.files.get("photos"):
            to_bucket = self.settings["qiniu_file_bucket"]
            to_key = "match:status:%s%s" % (match_id, time.time())
            to_key = hashlib.md5(to_key.encode()).hexdigest()
            photo_key = self.upload_file_to_qiniu(file,
                                                  to_bucket=to_bucket,
                                                  to_key=to_key)
            photo_keys_list.append(photo_key)
        return photo_keys_list


@admin_app.route(r"/matches", name="admin_matches")
class ListHandler(AdminBaseHandler):
    """ 赛事列表
    """

    def get(self):

        keyword = self.get_argument("kw", "")
        filter_state = intval(self.get_argument("state", -1))
        sort = intval(self.get_argument("sort", 0))

        query = Match.select()

        # 这里是根据 match.user_id 指向用户的区域进行的过滤
        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.join(
                User,
                on=(User.id == Match.user_id)
            ).where(
                User.province << self.current_user.valid_manage_provinces
            )

        # 已取消
        if filter_state == 0:
            query = query.where(Match.state ==
                                Match.MatchState.cancelled)

        # 等待审核
        elif filter_state == 1:
            query = query.where(Match.state ==
                                Match.MatchState.wait_review)
        # 进行中
        elif filter_state == 2:
            query = query.where(Match.state ==
                                Match.MatchState.opening)
        # 已结束
        elif filter_state == 3:
            query = query.where(Match.state ==
                                Match.MatchState.finished)

        if keyword:
            query = query.where(Match.title.contains(keyword))

        if sort == 2:
            query = query.order_by(Match.start_time.desc())
        else:
            query = query.order_by(Match.id.desc())

        matches = self.paginate_query(query)

        self.render("match/list.html",
                    matches=matches,
                    )


@admin_app.route(r"/matches/detail_action", name="admin_match_detail_action")
class MatchDetailActionHandler(AdminBaseHandler):

    """
    赛程详情页面上的操作
    """

    def _delete_round(self, round_id):
        MatchRound.delete()\
            .where(MatchRound.id == round_id)\
            .execute()
        self.write_success()

    def post(self):
        action = self.get_argument("action")

        if action == "delete_round":
            round_id = intval(self.get_argument("id", ""))
            self._delete_round(round_id)
        else:
            self.logger.error("用户在赛程详情页面尝试调用不存在的操作: %s" % action)


@admin_app.route(r"/matches/([\d]+)", name="admin_match_detail")
class DetailHandler(AdminBaseHandler):

    def get(self, match_id):
        match = Match.get_or_404(id=match_id)

        # 获取赛事分组信息
        groups = MatchGroup.select().where(
            MatchGroup.match_id == match.id
        ).order_by(
            MatchGroup.sort_num.desc()
        )

        # 获取报名表自定义选项
        custom_options = MatchOption.select().where(
            MatchOption.match_id == match.id
        ).order_by(
            MatchOption.sort_num.desc()
        )

        rounds = MatchRound.select(
            MatchRound,
        ).where(
            MatchRound.match_id == match.id
        ).order_by(
            MatchRound.created.asc(),
            MatchRound.id.asc()
        )

        covers = MatchCover.select().where(
            MatchCover.match_id == match.id
        ).order_by(
            MatchCover.id.desc()
        )

        # 获取对阵图
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

            againsts[against.round_id].append(against)

        self.render("match/detail.html",
                    match=match,
                    rounds=rounds,
                    groups=groups,
                    custom_options=custom_options,
                    covers=covers,
                    againsts=againsts
                    )

    def post(self, match_id):

        action = self.get_argument("action")
        match = Match.get_or_404(id=match_id)

        if action == "pass":
            Match.update(
                state=Match.MatchState.opening,
                updated=datetime.now()
            ).where(
                Match.id == match.id,
                Match.state << [Match.MatchState.wait_review,
                                Match.MatchState.in_review]
            ).execute()

        elif action == "reject":
            Match.update(
                state=Match.MatchState.rejected,
                reject_time=datetime.now(),
                reject_reason=self.get_argument("reject_reason", "")
            ).where(
                Match.id == match.id,
                Match.state << [Match.MatchState.wait_review,
                                Match.MatchState.in_review]
            ).execute()

        self.write_success()


@admin_app.route(r"/matches/([a-zA-Z0-9]+)/edit", name="admin_match_edit")
class EditHandler(AdminBaseHandler):
    """ 编辑赛事
    """

    def parse_groups(self):
        groups = {}
        for key in self.request.arguments:
            if key.startswith("group") and key not in ("group_type", ):
                value = self.get_argument(key)
                parts = key.split("_", 3)

                idx = int(parts[2])
                if idx not in groups:
                    groups[idx] = {
                        "id": 0,
                        "name": "",
                        "price": 0,
                        "max": 0
                    }

                if parts[1] in ("max", "id"):
                    value = intval(value)

                elif parts[1] in ('price', ):
                    value = decimalval(value)

                groups[idx][parts[1]] = value

        return [groups[idx] for idx in groups if groups[idx]['name']]

    def parse_options(self):
        """
        解析内置选项
        """
        options = []
        for field_type in MatchOption.BuiltinFieldTypes:
            value = self.get_argument("option_{0}".format(field_type.value), "")
            if value == "1":
                options.append(field_type.value)

        default_options = ['name', 'mobile']

        options = list(set(default_options + options))
        return [field_type.value
                for field_type in MatchOption.BuiltinFieldTypes
                if field_type.value in options]

    def parse_custom_options(self):
        """
        解析自定义选项
        """
        options = {}
        for key in self.request.arguments:
            if key.startswith("custom_option"):
                value = self.get_argument(key)
                parts = key.split("-")

                idx = int(parts[-1])
                if idx not in options:
                    options[idx] = {
                        "id": 0,
                        "title": "",
                        "field_type": "text",
                        "required": 0,
                        "choices": ""
                    }

                if parts[1] in ("required", "id"):
                    value = intval(value)

                options[idx][parts[1]] = value

        options = [options[idx] for idx in options if options[idx]['title']]
        for idx in range(0, len(options)):
            option = options[idx]
            if option['field_type'] not in ("multichoice", "choice"):
                option['choices'] = ""

            options[idx] = option

        return options

    def validate_groups(self, form, groups):
        group_type = intval(self.get_argument("group_type"))

        if group_type == 1:
            if len(groups) == 0:
                form.groups.errors = [ValidationError("至少需要添加一个分组")]
                return False
            else:
                for group in groups:
                    if intval(group['max']) <= 0:
                        form.groups.errors = [ValidationError("人数限制不能为零")]
                        return False

        else:
            max_members = intval(self.get_argument("max_members"))
            if max_members <= 0:
                form.max_members.errors = [ValidationError("不能为零")]
                return False

        return True

    def get(self, match_id):

        match = Match.get_or_404(id=match_id)
        match.sport_id = Sport.get_or_none(id=match.sport_id)

        match.group_type = str(match.group_type)
        team = Team.get_or_404(id=match.team_id)
        form = EditMatchFrom(obj=match, team=team)

        # 获取赛事分组信息
        query = MatchGroup.select().where(
            MatchGroup.match_id == match.id
        ).order_by(
            MatchGroup.sort_num.desc()
        )

        groups = []
        for group in query:
            group = group.info
            group['max'] = group['max_members']
            groups.append(group)

        # 获取报名表自定义选项
        query = MatchOption.select().where(
            MatchOption.match_id == match.id
        ).order_by(
            MatchOption.sort_num.desc()
        )

        custom_options = []
        for option in query:
            option = option.info
            if 'choices' in option:
                option['choices'] = "|".join(option['choices'])
            custom_options.append(option)

        self.render("match/edit.html",
                    form=form,
                    match=match,
                    cities=ChinaCity.get_cities(),
                    group_type=match.group_type,
                    groups=groups,
                    custom_options=custom_options,
                    options=match.fields
                    )

    def post(self, match_id):
        match = Match.get_or_404(id=match_id)
        team = Team.get_or_404(id=match.team_id)
        form = EditMatchFrom(self.arguments, team=team)

        groups = self.parse_groups()
        options = self.parse_options()
        custom_options = self.parse_custom_options()

        # 验证分组设置
        groups_validated = self.validate_groups(form, groups)

        if form.validate() and groups_validated:
            with(self.db.transaction()):
                form.populate_obj(match)

                # 计算赛事总人数限制
                if intval(match.group_type) == 1:
                    match.price = min(map(lambda x: float(x['price']), groups)) if groups else 0
                    match.max_members = reduce(lambda x, y: x + y, map(lambda x: x['max'], groups)) if groups else 0

                if "coverfile" in self.request.files:
                    to_bucket = self.settings['qiniu_avatar_bucket']
                    to_key = "match:%s%s" % (self.current_user.id, time.time())
                    to_key = hashlib.md5(to_key.encode()).hexdigest()

                    cover_key = self.upload_file("coverfile",
                                                 to_bucket=to_bucket,
                                                 to_key=to_key,
                                                 )

                    match.cover_key = cover_key

                match.user_id = self.current_user.id
                match.fields = options

                if not match.join_end:
                    match.join_end = match.start_time

                match.save()

                if intval(match_id) > 0:
                    group_ids = [group['id'] for group in groups
                                 if group['id'] > 0]

                    if len(group_ids) > 0:
                        MatchGroup.delete().where(
                            MatchGroup.match_id == intval(match_id),
                            MatchGroup.id.not_in(group_ids)
                        ).execute()

                    else:
                        MatchGroup.delete().where(
                            MatchGroup.match_id == intval(match_id)
                        ).execute()

                # 保存分组
                for group in groups:
                    if group['id'] > 0:
                        MatchGroup.update(
                            name=group['name'],
                            price=group['price'],
                            max_members=group['max']
                        ).where(
                            MatchGroup.id == group['id']
                        ).execute()

                    else:
                        MatchGroup.create(
                            match_id=match.id,
                            name=group['name'],
                            price=group['price'],
                            max_members=group['max']
                        )

                if intval(match_id) > 0:
                    custom_option_ids = [custom_option['id'] for custom_option in
                                         custom_options if custom_option['id'] > 0]

                    if len(custom_option_ids) > 0:
                        MatchOption.delete().where(
                            MatchOption.match_id == intval(match_id),
                            MatchOption.id.not_in(custom_option_ids)
                        ).execute()

                    else:
                        MatchOption.delete().where(
                            MatchOption.match_id == intval(match_id)
                        ).execute()

                # 保存自定义选项
                for custom_option in custom_options:
                    if custom_option['id'] > 0:
                        MatchOption.update(
                            title=custom_option['title'],
                            field_type=custom_option['field_type'],
                            required=custom_option['required'],
                            choices=custom_option['choices'],
                        ).where(
                            MatchOption.id == custom_option['id']
                        ).execute()
                    else:
                        MatchOption.create(
                            match_id=match.id,
                            title=custom_option['title'],
                            field_type=custom_option['field_type'],
                            required=custom_option['required'],
                            choices=custom_option['choices'],
                        )

            # MatchService.add_match_start_notify(match)
            self.redirect(self.reverse_url("admin_match_detail", match.id))
            return

        province = self.get_argument("province", None)
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.validate_groups(form, groups)

        self.render("match/edit.html",
                    form=form,
                    match=match,
                    cities=ChinaCity.get_cities(),
                    groups=groups,
                    group_type=self.get_argument("group_type", "0"),
                    options=options,
                    custom_options=custom_options
                    )


@admin_app.route(r"/matches/upload_image", name="admin_matches_upload_image")
class UploadImageHandler(AdminBaseHandler):

    def post(self):
        to_bucket = self.settings['qiniu_file_bucket']
        to_key = "match:rules:image:%s%s" % (self.current_user.id, time.time())
        to_key = hashlib.md5(to_key.encode()).hexdigest()
        image_key = self.upload_file('image',
                                     to_bucket=to_bucket,
                                     to_key=to_key)
        url_dict = Match.get_cover_urls(image_key)

        if url_dict:
            mini_url = url_dict['url'] + url_dict['sizes'][0]
        else:
            mini_url = ""
        self.write(mini_url)


@admin_app.route(r"/matches/(\d+)/members", name="admin_match_members_list")
class MembersHandler(AdminBaseHandler):
    """ 比赛报名成员列表
    """

    def get(self, match_id):
        match = Match.get_or_404(id=match_id)

        query = MatchMember.select(
            MatchMember,
            MatchGroup
        ).join(
            MatchGroup,
            join_type=JOIN_LEFT_OUTER,
            on=(MatchMember.group_id == MatchGroup.id).alias("group")
        ).where(
            MatchMember.match_id == match.id
        ).order_by(MatchMember.id.desc())

        group_query = MatchGroup.select() \
            .where(MatchGroup.match_id == match_id)
        self.logger.debug(group_query.sql())
        groups = []
        for group in group_query:
            groups.append({"name": group.name})

        group_name = self.get_argument("group_name", "")
        if group_name:
            query = query.where(MatchGroup.name == group_name)

        members = self.paginate_query(query)

        sum_fee = MatchMember.select(
            fn.SUM(MatchMember.total_fee).alias("sum")
        ).where(
            MatchMember.match_id == match_id
        ).scalar()

        self.render("match/match_members_list.html",
                    sum_fee=sum_fee,
                    groups=groups,
                    match=match,
                    members=members,
                    pagination=members.pagination
                    )


@admin_app.route(r"matches/(\d+)/members/export",
                 name="admin_export_matches_apply_form")
class ExportMatchMembersHandler(AdminBaseHandler):
    """
    导出比赛报名成员列表
    """

    def get(self, match_id):
        members = MatchMember.select(
            MatchMember,
            MatchGroup
        ).join(
            MatchGroup,
            join_type=JOIN_LEFT_OUTER,
            on=(MatchMember.group_id == MatchGroup.id).alias("group")
        ).where(
            MatchMember.match_id == match_id
        ).order_by(MatchMember.id.desc())

        # display_fields = ("name")
        #
        # with Workbook("temp.xls") as workbook:
        #     worksheet = workbook.add_worksheet()
        #     worksheet.write_row(0, 0, )
        #     for member in members:
        #
        #
        # self.write()
        self.write_success()


@admin_app.route(r"/matches/members_action", name="admin_match_members_list_action")
class MatchMembersListActionHandler(AdminBaseHandler):

    """
    比赛成员列表中的操作
    """

    def _approve(self, member_id):
        # 通过审核
        member = MatchMember.get_or_404(id=member_id)
        member.set_approved()
        member.save()
        self.write_success()

    def _reject(self, member_id):
        # 审核不通过，如果已经付款的需要退款
        member = MatchMember.get_or_404(id=member_id)
        member.set_reject()
        member.save()
        self.write_success()

    def _request_for_improved(self, member_id):
        # 提示用户完善信息
        member = MatchMember.get_or_404(id=member_id)
        member.set_request_for_improved()
        member.save()
        self.write_success()

    def _ban(self, member_id):
        """
        ban 成员，并保存原有状态
        """

        member = MatchMember.get_or_404(id=member_id)

        if member.state == MatchMember.MatchMemberState.banned:
            self.write_success()
        else:
            MatchMember.update(
                state=MatchMember.MatchMemberState.banned,
                state_before_ban=member.state
            ).where(
                MatchMember.id == member_id
            ).execute()
            self.write_success()

    def _unban(self, member_id):
        """
        unban 成员，并恢复到 ban 时原状态
        """

        member = MatchMember.get_or_404(id=member_id)

        if member.state != MatchMember.MatchMemberState.banned:
            self.write_success()
        else:
            MatchMember.update(
                state=member.state_before_ban
            ).where(
                MatchMember.id == member_id
            ).execute()
            self.write_success()

    def post(self):
        member_id = intval(self.get_argument("id", ""))
        action = self.get_argument("action", "")

        if action == "ban":
            self._ban(member_id)
        elif action == "unban":
            self._unban(member_id)
        elif action == "approve":
            self._approve(member_id)
        elif action == "reject":
            self._reject(member_id)
        elif action == "request_for_improved":
            self._request_for_improved(member_id)
        else:
            self.logger.debug("用户在赛事成员列表尝试进行不存在的操作: %s" % action)


@admin_app.route(r"/matches/(\d+)/statuses", name="admin_match_statuses")
class MatchStatusesHandler(AdminBaseHandler):

    def get(self, match_id):

        match = Match.get_or_404(id=match_id)

        query = MatchStatus.select(
            MatchStatus,
        ).where(
            MatchStatus.match_id == match.id
        ).order_by(MatchStatus.created.desc())

        statuses = self.paginate_query(query)

        self.render("match/statuses.html",
                    statuses=statuses,
                    match=match
                    )


@admin_app.route(r"/matches/(\d+)/statuses/add", name="admin_match_statuses_add")
class MatchStatusesAddHandler(AdminBaseHandler, MatchStatusHandlerMixin):

    """
    添加新的动态
    """

    def get(self, match_id):
        match = Match.get_or_404(id=match_id)
        form = MatchStatusForm()

        self.render("match/statuses_add.html",
                    match=match,
                    form=form)

    def post(self, match_id):
        match = Match.get_or_404(id=match_id)
        form = MatchStatusForm(self.arguments)

        if not form.validate():
            self.render("match/statuses_add.html",
                        match=match,
                        form=form)
        else:
            status = MatchStatus(match_id=match_id)
            form.populate_obj(status)

            if "photos" in self.request.files:
                photo_keys_list = self.upload_photos(match_id)
            else:
                photo_keys_list = []

            status.photos = photo_keys_list
            status.save()

            self.redirect(self.reverse_url("admin_match_statuses", match_id))


@admin_app.route(r"/matchs/(\d+)/statuses/(\d+)/edit",
                 name="admin_match_statuses_edit")
class MatchStatusesEditHandler(AdminBaseHandler, MatchStatusHandlerMixin):

    """
    修改赛事状态
    """

    def get(self, match_id, status_id):
        match = Match.get_or_404(id=match_id)
        status = MatchStatus.get_or_404(id=status_id)

        form = MatchStatusForm(obj=status)
        self.render("match/statuses_edit.html",
                    match=match,
                    status=status,
                    form=form)

    def post(self, match_id, status_id):
        match = Match.get_or_404(id=match_id)
        status = MatchStatus.get_or_404(id=status_id)
        delete_photo_keys = self.get_argument("delete-photo-keys", "")

        form = MatchStatusForm(self.arguments)

        if not form.validate():
            self.render("match/statuses_edit.html",
                        match=match,
                        status=status,
                        form=form)
        else:
            if delete_photo_keys:
                delete_photo_keys_list = delete_photo_keys.split(",")
            else:
                delete_photo_keys_list = []

            if "photos" in self.request.files:
                photo_keys_list = self.upload_photos(match_id)
            else:
                photo_keys_list = []

            new_photos_set = set(status.photos) ^ set(delete_photo_keys_list)
            new_photos_set = new_photos_set.union(set(photo_keys_list))

            form.populate_obj(status)
            status.photos = list(new_photos_set)
            status.save()

            self.redirect(self.reverse_url("admin_match_statuses", match_id))


@admin_app.route(r"/matchs/statuses/list_action",
                 name="admin_match_statuses_list_action")
class MatchStatusesListActionsHandler(AdminBaseHandler):

    """
    赛事动态列表相关操作
    """

    def _delete(self, id):
        MatchStatus.delete()\
            .where(MatchStatus.id == id)\
            .execute()
        self.write_success()

    def post(self):
        action = self.get_argument("action", "")
        status_id = intval(self.get_argument("id", ""))

        if action == "delete":
            self._delete(status_id)
        else:
            self.logger.warning("用户在赛事动态列表中尝试调用不存在的操作: %s", action)
            self.write_success()


@admin_app.route(r"/matches/(\d+)/create_round", name="admin_round_create")
class MatchCreateRoundHandler(AdminBaseHandler):

    def get(self, match_id):

        match = Match.get_or_404(id=match_id)
        match_round = MatchRound(
            match_id=match_id
        )

        form = CreateRoundForm(obj=match_round)

        self.render("match/round_create.html",
                    form=form,
                    match=match
                    )

    @tornado.gen.coroutine
    def post(self, match_id):

        match = Match.get_or_404(id=match_id)
        form = CreateRoundForm(self.arguments)

        match_round = MatchRound(match_id=match.id)
        if form.validate():
            form.populate_obj(match_round)
            match_round.save()

            service.match.MatchService.add_match_status_notify(match)
            self.redirect(self.reverse_url("admin_match_detail", match_id))
            return

        self.render("match/round_create.html",
                    form=form,
                    match=match
                    )


@admin_app.route(r"/matches/(\d+)/add_cover", name="admin_round_add_cover")
class MatchAddCoverRoundHandler(AdminBaseHandler):

    def get(self, match_id):

        match = Match.get_or_404(id=match_id)
        cover = MatchCover(
            match_id=match_id
        )

        form = CreateCoverForm(obj=cover)

        self.render("match/add_cover.html",
                    form=form,
                    match=match
                    )

    @tornado.gen.coroutine
    def post(self, match_id):

        match = Match.get_or_404(id=match_id)
        form = CreateCoverForm(self.arguments)

        if form.validate():

            cover = MatchCover(match_id=match.id)
            form.populate_obj(cover)

            if "coverfile" in self.request.files:
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "match:cover:%s%s" % (match_id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                cover_key = self.upload_file("coverfile",
                                             to_bucket=to_bucket,
                                             to_key=to_key,
                                             )

                cover.cover_key = cover_key

            cover.save()

            self.redirect(self.reverse_url("admin_match_detail", match_id))
            return

        self.render("match/add_cover.html",
                    form=form,
                    match=match
                    )


@admin_app.route(r"/rounds/(\d+)/edit", name="admin_round_edit")
class MatchRoundEditHandler(AdminBaseHandler):

    def get(self, round_id):

        match_round = MatchRound.get_or_404(id=round_id)
        match = Match.get_or_404(id=match_round.match_id)

        form = EditRoundForm(obj=match_round)

        self.render("match/round_edit.html",
                    form=form,
                    match=match
                    )

    @tornado.gen.coroutine
    def post(self, round_id):
        match_round = MatchRound.get_or_404(id=round_id)
        match = Match.get_or_404(id=match_round.match_id)
        form = EditRoundForm(self.arguments)

        if form.validate():
            form.populate_obj(match_round)
            match_round.save()

            self.redirect(self.reverse_url("admin_match_detail", match.id))
            return

        self.render("match/round_edit.html",
                    form=form,
                    match=match
                    )


@admin_app.route(r"/rounds/(\d+)/againsts", name="admin_round_againsts")
class MatchRoundAgainstsHandler(AdminBaseHandler):

    """
    轮次对阵图
    """

    def get(self, round_id):

        match_round = MatchRound.get_or_404(id=round_id)
        match = Match.get_or_404(id=match_round.match_id)

        query = MatchMember.select().where(
            MatchMember.match_id == match.id,
            MatchMember.state == MatchMember.MatchMemberState.normal
        )

        members = []
        for member in query:
            members.append({
                "id": member.id,
                "name": member.name
            })

        query = MatchAgainst.select().where(
            MatchAgainst.round_id == match_round.id
        ).order_by(
            MatchAgainst.id.asc()
        )

        againsts = []
        for against in query:
            againsts.append(against.info)

        match_options = MatchOption.select().where(
            MatchOption.match_id == match.id
        )

        self.render("match/round_againsts.html",
                    match=match,
                    match_round=match_round,
                    members=members,
                    againsts=againsts,
                    match_options=match_options
                    )

    def post(self, round_id):

        match_round = MatchRound.get_or_404(id=round_id)
        match = Match.get_or_404(id=match_round.match_id)

        againsts = {}
        for key in self.request.arguments:
            if key.startswith("ag-"):
                value = self.get_argument(key)
                parts = key.split("-")

                idx = int(parts[-1])
                if idx not in againsts:
                    againsts[idx] = {
                        "left": 0,
                        "right": 0,
                        "address": "",
                        "start_time": "",
                        "left_score": 0,
                        "right_score": 0
                    }

                if parts[1] in ("left", "right", "left_score", "right_score"):
                    value = intval(value)

                elif parts[1] in ("start_time", ) and value == "":
                    raise ArgumentError(400, "请填写对战时间")

                elif parts[1] in ("address", ) and value == "":
                    raise ArgumentError(400, "请填写对战地址")

                againsts[idx][parts[1]] = value

        # 清除旧的
        MatchAgainst.delete().where(
            MatchAgainst.round_id == match_round.id
        ).execute()

        againsts = [againsts[idx] for idx in againsts if againsts[idx]['left']]

        start_time = None
        end_time = None
        for against in againsts:
            if against['left_score'] > against['left_score']:
                win_member_id = against['left']

            elif against['left_score'] < against['left_score']:
                win_member_id = against['right']

            elif against['left_score'] == against['left_score']:
                win_member_id = 0

            MatchAgainst.create(
                match_id=match.id,
                round_id=match_round.id,
                left_member_id=intval(against['left']),
                right_member_id=intval(against['right']),
                address=against['address'],
                left_score=intval(against['left_score']) or "0",
                right_score=intval(against['right_score']) or "0",
                win_member_id=win_member_id,
                start_time=against['start_time'] if against['start_time'] else None
            )

            if not start_time or against['start_time'] < start_time:
                start_time = against['start_time']

            if not end_time or against['start_time'] > end_time:
                end_time = against['start_time']

        if match.type == 0:
            MatchRound.update(
                start_time=start_time,
                end_time=end_time
            ).where(
                MatchRound.id == match_round.id
            ).execute()

        self.write_success()


@admin_app.route(r"/settlement_applications",
                 name="admin_settlement_applications")
class SettlementApplicationsHandler(AdminBaseHandler):

    """
    结算申请
    """

    def get(self):
        query = SettlementApplication.select(
            SettlementApplication,
            Match,
            Team,
            User
        ).join(
            Match, on=(SettlementApplication.match_id == Match.id).alias("match")
        ).switch(
            SettlementApplication
        ).join(
            Team,
            on=(SettlementApplication.team_id == Team.id).alias("team")
        ).switch(
            SettlementApplication
        ).join(
            User,
            on=(SettlementApplication.user_id == User.id).alias("user")
        ).order_by(
            SettlementApplication.created.desc()
        )

        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.where(
                User.province << self.current_user.valid_manage_provinces
            )

        applications = self.paginate_query(query)
        self.render("match/settlement_applications_list.html",
                    applications=applications)


@admin_app.route(r"/settlement_applications_action",
                 name="admin_settlement_applications_action")
class SettlementApplicationsActionHandler(AdminBaseHandler):

    """
    结算申请列表操作
    """

    def approve(self, application_id):
        application = SettlementApplication.get_or_404(id=application_id)
        service.match.SettlementService.approve(application,
                                                self.current_user)
        self.write_success()

    def disapprove(self, application_id):
        application = SettlementApplication.get_or_404(id=application_id)
        service.match.SettlementService.disapprove(application,
                                                   self.current_user)
        self.write_success()

    def post(self):
        action = self.get_argument("action", "")
        application_id = intval(self.get_argument("id", ""))
        if action == "approve":
            self.approve(application_id)
        elif action == "disapprove":
            self.disapprove(application_id)
        else:
            self.logger.error("用户在结算申请列表尝试不存在的操作：%s" % action)
