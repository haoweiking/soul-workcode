import hashlib
import io
import os
import time
import uuid
from functools import reduce
from typing import IO

import tornado.escape
import tornado.gen
import tornado.web
from peewee import JOIN_LEFT_OUTER, fn
from wtforms import ValidationError
from xlsxwriter import Workbook

from yiyun import service
from yiyun import tasks
from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile, intval, decimalval
from yiyun.models import (Match, Sport,
                          ChinaCity, MatchRound,
                          MatchStatus, MatchMember, MatchOption,
                          MatchGroup, MatchCover, MatchAgainst,
                          SettlementApplication)
from .base import ClubBaseHandler, club_app
from .forms.match import (CreateMatchFrom, EditMatchFrom, CreateRoundForm,
                          EditRoundForm, CreateCoverForm, MatchStatusForm)
from yiyun.service.match import MatchService


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


@club_app.route(r"/matches", name="club_matches")
class ListHandler(ClubBaseHandler):
    """ 赛事列表
    """

    def get(self):

        keyword = self.get_argument("kw", "")
        filter_state = intval(self.get_argument("state", -1))
        sort = intval(self.get_argument("sort", 0))

        query = Match.select(
            Match,
        ).where(
            Match.team_id == self.current_team.id
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


@club_app.route(r"/matches/create", name="club_matches_create")
class CreateHandler(ClubBaseHandler):
    """ 创建赛事
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
            value = self.get_argument(
                "option_{0}".format(field_type.value), "")
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

    def get(self):

        match = Match(
            team_id=self.current_team.id,
            contact_person=self.current_team.contact_person,
            contact_phone=self.current_team.contact_phone,
            province=self.current_team.province,
            city=self.current_team.city,
            address=self.current_team.address
        )

        form = CreateMatchFrom(obj=match, team=self.current_team)

        self.render("match/create.html",
                    match=match,
                    form=form,
                    cities=ChinaCity.get_cities(),
                    groups=[],
                    group_type=0,
                    options=[],
                    custom_options=[]
                    )

    def post(self, match_id=None):

        if match_id:
            form = EditMatchFrom(self.arguments, team=self.current_team)
            match = Match.get_or_404(id=match_id)
        else:
            form = CreateMatchFrom(self.arguments, team=self.current_team)
            match = Match(team_id=self.current_team.id)

        groups = self.parse_groups()
        options = self.parse_options()
        custom_options = self.parse_custom_options()

        # 验证分组设置
        groups_validated = self.validate_groups(form, groups)

        cover_validated = True
        cover_key = None
        if "coverfile" in self.request.files:
            to_bucket = self.settings['qiniu_avatar_bucket']
            to_key = "match:%s%s" % (self.current_user.id, time.time())
            to_key = hashlib.md5(to_key.encode()).hexdigest()

            try:
                cover_key = self.upload_file("coverfile",
                                             to_bucket=to_bucket,
                                             to_key=to_key,
                                             )
            except Exception as e:
                form.coverfile.errors = [ValidationError("%s" % e)]
                cover_validated = False

        if form.validate() and groups_validated \
                and cover_validated:

            with(self.db.transaction()):
                form.populate_obj(match)

                # 计算赛事总人数限制
                if intval(match.group_type) == 1:
                    match.price = min(
                        map(lambda x: float(x['price']), groups)) if groups else 0
                    match.max_members = reduce(
                        lambda x, y: x + y, map(lambda x: x['max'], groups)) if groups else 0

                if cover_key:
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

            # service.match.MatchService.add_match_start_notify(match)
            self.redirect(self.reverse_url("club_match_detail", match.id))
            return

        province = self.get_argument("province", None)
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.validate_groups(form, groups)

        if match_id:
            tpl = "match/edit.html"
        else:
            tpl = "match/create.html"

        self.render(tpl,
                    form=form,
                    match=match,
                    cities=ChinaCity.get_cities(),
                    groups=groups,
                    group_type=self.get_argument("group_type", "0"),
                    options=options,
                    custom_options=custom_options
                    )


@club_app.route(r"/matches/([a-zA-Z0-9]+)/edit", name="club_matches_edit")
class EditHandler(CreateHandler):
    """ 编辑赛事
    """

    def get(self, match_id):

        match = Match.get_or_404(id=match_id)
        match.sport_id = Sport.get_or_none(id=match.sport_id)

        match.group_type = str(match.group_type)
        form = EditMatchFrom(obj=match, team=self.current_team)

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


@club_app.route(r"/matches/upload_image", name="club_matches_upload_image")
class UploadImageHandler(ClubBaseHandler):

    def post(self):

        base_url = self.settings['attach_url']
        to_bucket = self.settings['qiniu_file_bucket']

        to_key = "match:rules:image:%s%s" % (self.current_user.id, time.time())
        to_key = hashlib.md5(to_key.encode()).hexdigest()
        image_key = self.upload_file('image',
                                     to_bucket=to_bucket,
                                     to_key=to_key)

        url_dict = Match.get_cover_urls(image_key,
                                        cover_url=base_url,
                                        crop=False)

        if url_dict:
            mini_url = url_dict['url'] + url_dict['sizes'][2]
        else:
            mini_url = ""
            
        self.write(mini_url)


@club_app.route(r"/matches/(\d+)/disable", name="club_matches_disable")
class DisableMatchHandler(ClubBaseHandler):
    """
    取消赛事
    """

    def post(self, match_id):
        match = Match.get_or_404(id=match_id)
        MatchService.cancel(match, self.current_user)
        self.write_success()


@club_app.route(r"/matches/detail_action", name="club_match_detail_action")
class MatchDetailActionHandler(ClubBaseHandler):

    """
    赛程详情页面上的操作
    """

    def _settlement_application(self, match_id):
        # 提交结算申请
        match = Match.get_or_404(id=match_id)
        if not match.can_apply_settlement():
            self.write_error(403, "此活动不能手动结算")
        else:
            MatchService.settlement_application(self.current_user, match)
            self.write_success()

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
        elif action == "settlement_application":
            match_id = intval(self.get_argument("id"))
            self._settlement_application(match_id)
        else:
            self.logger.error("用户在赛程详情页面尝试调用不存在的操作: %s" % action)


@club_app.route(r"/matches/([\d]+)", name="club_match_detail")
class MatchDetailHandler(ClubBaseHandler):
    """赛事详细信息"""

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
            MatchMember, on=(MatchAgainst.left_member_id ==
                             MatchMember.id).alias("left_member")
        ).switch(
            MatchAgainst
        ).join(
            RightMember,
            join_type=JOIN_LEFT_OUTER,
            on=(MatchAgainst.right_member_id ==
                RightMember.id).alias("right_member")
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

        # 如果已经结束 获取是否已经提交了结算申请
        is_application_exist =\
            SettlementApplication.is_application_exist(match_id)

        self.render("match/detail.html",
                    match=match,
                    rounds=rounds,
                    groups=groups,
                    custom_options=custom_options,
                    covers=covers,
                    againsts=againsts,
                    is_application_exist=is_application_exist
                    )


@club_app.route(r"/matches/(\d+)/preview_qr.jpg", name="club_match_preview_qr")
class MatchPreviewQr(ClubBaseHandler):
    """
    预览赛事二维码
    """

    def get(self, match_id):
        match = Match.get_or_404(id=match_id)
        qr = MatchService.get_preview_qrcode(match.id)
        o = io.BytesIO()
        qr.save(o, format="JPEG")
        qr_obj = o.getvalue()
        o.close()

        self.set_header('Expires', '0')
        self.set_header(
            'Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(qr_obj))
        self.write(qr_obj)


@club_app.route(r"/matches/(\d+)/members", name="club_match_members_list")
class MatchMembersListHandler(ClubBaseHandler):
    """ 比赛报名成员列表
    """

    def get(self, match_id):
        keyword = self.get_argument("kw", "")
        match = Match.get_or_404(id=match_id)
        query = MatchMember.query_all_members(match_id)

        group_query = MatchGroup.select() \
            .where(MatchGroup.match_id == match_id)
        self.logger.debug(group_query.sql())
        groups = []
        for group in group_query:
            groups.append({"name": group.name})

        group_name = self.get_argument("group_name", "")
        if group_name:
            query = query.where(MatchGroup.name == group_name)

        if keyword:
            if is_mobile(keyword):
                query = query.where(MatchMember.mobile == keyword)
            else:
                query = query.where(MatchMember.name.contains(keyword))

        members = self.paginate_query(query)

        sum_fee = MatchMember.select(
            fn.SUM(MatchMember.total_fee).alias("sum")
        ).where(
            MatchMember.match_id == match_id
        ).scalar()

        self.render("match/match_members_list.html",
                    sum_fee=sum_fee,
                    match=match,
                    groups=groups,
                    members=members,
                    pagination=members.pagination
                    )


@club_app.route(r"/matches/(\d+)/members/(all|normal)/export",
                name="club_export_matches_apply_form")
class ExportMatchMembersHandler(ClubBaseHandler):
    """
    导出比赛报名成员列表
    """

    def get(self, match_id, state):
        match = Match.get_or_404(id=match_id)

        if state == "normal":
            # 查询正常参赛成员
            members = MatchMember\
                .query_all_members(match_id)\
                .where(MatchMember.state == MatchMember.MatchMemberState.normal)
        else:
            members = MatchMember.query_all_members(match_id)

        # 文件或图片
        def is_file(option_info):
            if option_info.is_idcard_photo() or \
                    option_info.is_avatar() or \
                    option_info.is_file() or \
                    option_info.is_photo():
                return True
            return False

        # 排除文件和图片项
        option_info_list = [option_info for option_info in match.option_info_list
                            if not is_file(option_info)]

        option_name_list = [option_info.option_name
                            for option_info in option_info_list if not is_file(option_info)]
        option_name_list.extend(["报名时间", "状态"])

        file_name = "{match_name}成员列表.xlsx"\
            .format(match_name=match.title)
        # temp_file_name = str(uuid.uuid4())

        o = io.BytesIO()
        with Workbook(o) as workbook:
            worksheet = workbook.add_worksheet()
            row, col = 0, 0
            worksheet.write_row(row, col, option_name_list)
            for member in members:
                row, col = row + 1, 0
                assert isinstance(member, MatchMember)
                for option_info in option_info_list:
                    option_value = option_info.get_option_value(member)
                    # 处理布尔值显示
                    if option_info.is_leader_check() or option_info.is_boolean():
                        option_value = "是" if option_value else "否"
                    if option_info.is_gender():
                        option_value = member.display_gender()
                    if is_file(option_info) or \
                            isinstance(option_value, (list, dict, set)):
                        continue

                    worksheet.write(row, col, option_value)
                    col += 1
                worksheet.write(row, col, member.created.strftime('%Y.%m.%d'))
                worksheet.write(row, col + 1, member.state_name)

        data = o.getvalue()
        o.close()

        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition",
                        "attachment; filename={0}".format(file_name))
        self.add_header("Content-Length", len(data))
        self.set_header("Content-Transfer-Encoding", "binary")
        self.write(data)


@club_app.route(r"/matches/members_action", name="club_match_members_list_action")
class MatchMembersListActionHandler(ClubBaseHandler):

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

            Match.update_members_count(member.match_id)
            self.write_success()

    def _unban(self, member_id):
        """
        unban 成员，并恢复到 ban 时原状态
        """

        member = MatchMember.get_or_404(id=member_id)
        match = Match.get_or_404(id=member.match_id)

        if member.state != MatchMember.MatchMemberState.banned:
            self.write_success()
        else:
            # 判断是不是人数已满等 以确定是否可以恢复
            res = match.can_join()
            if res["can"]:
                MatchMember.update(
                    state=member.state_before_ban
                ).where(
                    MatchMember.id == member_id
                ).execute()
                Match.update_members_count(member.match_id)

                self.write_success()
            else:
                self.set_status(403)
                self.write({"reason": res["reason"]})

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


@club_app.route(r"/matches/(\d+)/statuses", name="club_match_statuses")
class MatchStatusesHandler(ClubBaseHandler):

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


@club_app.route(r"/matches/(\d+)/statuses/add", name="club_match_statuses_add")
class MatchStatusesAddHandler(ClubBaseHandler, MatchStatusHandlerMixin):

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

            self.redirect(self.reverse_url("club_match_statuses", match_id))


@club_app.route(r"/matchs/(\d+)/statuses/(\d+)/edit", name="club_match_statuses_edit")
class MatchStatusesEditHandler(ClubBaseHandler, MatchStatusHandlerMixin):

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

            self.redirect(self.reverse_url("club_match_statuses", match_id))


@club_app.route(r"/matchs/statuses/list_action", name="club_match_statuses_list_action")
class MatchStatusesListActionsHandler(ClubBaseHandler):

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


@club_app.route(r"/matches/(\d+)/create_round", name="club_round_create")
class MatchCreateRoundHandler(ClubBaseHandler):

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
            self.redirect(self.reverse_url("club_match_detail", match_id))
            return

        self.render("match/round_create.html",
                    form=form,
                    match=match
                    )


@club_app.route(r"/matches/(\d+)/add_cover", name="club_round_add_cover")
class MatchAddCoverRoundHandler(ClubBaseHandler):
    """添加海报"""

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

            try:
                cover = MatchCover(match_id=match.id)
                form.populate_obj(cover)

                if "coverfile" in self.request.files:
                    to_bucket = self.settings['qiniu_avatar_bucket']
                    to_key = "match:cover:%s%s" % (match_id, time.time())
                    to_key = hashlib.md5(to_key.encode()).hexdigest()

                    try:
                        cover_key = self.upload_file("coverfile",
                                                     to_bucket=to_bucket,
                                                     to_key=to_key,
                                                     )

                        cover.cover_key = cover_key
                    except Exception as e:
                        form.coverfile.errors = [ValidationError("%s" % e)]
                        raise e

                cover.save()

                self.redirect(self.reverse_url("club_match_detail", match_id))
                return

            except Exception as e:
                pass

        self.render("match/add_cover.html",
                    form=form,
                    match=match
                    )


@club_app.route(r"/matches/(\d+)/delete_cover", name="club_match_delete_cover")
class MatchDeleteCoverHandler(ClubBaseHandler):
    """删除海报"""

    @tornado.gen.coroutine
    def post(self, match_id):
        cover_id = self.get_argument("cover_id")
        match_cover = MatchCover.get_or_404(id=cover_id,
                                            match_id=match_id)
        bucket_name, key = match_cover.cover_key.split(":")

        with self.db.transaction():
            match_cover.delete_instance()
            ret, info = tasks.qiniu_tool.delete_file(bucket_name, key)
            if not ret:
                self.logger.debug("删除海报失败: %s" % info)
                raise ArgumentError(500, "删除失败")
        self.write_success()


@club_app.route(r"/rounds/(\d+)/edit", name="club_round_edit")
class MatchRoundEditHandler(ClubBaseHandler):

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

            self.redirect(self.reverse_url("club_match_detail", match.id))
            return

        self.render("match/round_edit.html",
                    form=form,
                    match=match
                    )


@club_app.route(r"/rounds/(\d+)/againsts", name="club_round_againsts")
class MatchRoundAgainstsHandler(ClubBaseHandler):

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
                start_time=against['start_time'] if against[
                    'start_time'] else None
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
