import logging
import hashlib
import time
from yiyun.libs.peewee_filter import (Filter, StringFiltering)
from yiyun.libs.parteam import Parteam
from yiyun.models import Team, TeamMember, TeamMemberGroup, TeamFollower
from .base import (rest_app, BaseClubAPIHandler, authenticated,
                   validate_arguments_with, ApiException)
from .schemas import team as schema
from .serializers.team import (SimpleTeamSerializer, TeamSerializer,
                               SimpleMemberSerializer, InsecureMemberSerializer)
from yiyun.service.team import TeamMemberGroupService, TeamService


class TeamFilter(Filter):

    keyword = StringFiltering(source='name', lookup_type='regexp')

    class Meta:
        fields = ('type', 'city', 'keyword', )


@rest_app.route(r'/teams')
class TeamModelHandler(BaseClubAPIHandler):

    filter_classes = (TeamFilter,)

    def check_create_throttle(self):
        """
        一个用户只允许创建一个俱乐部
        """
        count = Team.select()\
            .where(Team.owner_id == self.current_user.id)\
            .count()
        if count == 0:
            return True
        raise ApiException(400, "已创建的俱乐部数量 [{0}] 超限".format(count))

    def get(self):
        """获取俱乐部列表"""
        query = Team.select()
        query = self.filter_query(query)
        page = self.paginate_query(query)

        data = self.get_paginated_data(page=page, alias='teams',
                                       serializer=SimpleTeamSerializer)
        self.write(data)

    @validate_arguments_with(schema.create_team)
    @authenticated
    def post(self, *args, **kwargs):

        # 检查创建数量是否超限
        self.check_create_throttle()

        form = self.validated_arguments
        team = Team.create(owner_id=self.current_user.id, **form)

        self.set_status(201)
        self.write(TeamSerializer(instance=team).data)


@rest_app.route(r'/teams/(\d+)')
class TeamObjectHandler(BaseClubAPIHandler):

    def has_update_permission(self, team):
        """
        是否具有修改权限
        目前只有俱乐部所有者可以修改
        :param team: Team
        """
        # TODO: 俱乐部的管理员如果具有修改权限也可以修改
        if self.current_user == team.owner:
            return True
        raise ApiException(403, "无权修改俱乐部")

    def get(self, team_id):
        """获取俱乐部详情"""

        obj = Team.get_or_404(id=team_id)
        info = TeamSerializer(instance=obj, request=self).data

        if self.current_user and \
                TeamFollower.select().where(
                    TeamFollower.user_id == self.current_user.id,
                    TeamFollower.team_id == obj.id
                ).exists():
            info['is_following'] = True

        else:
            info['is_following'] = False

        self.write(info)

    @validate_arguments_with(schema.patch_team)
    @authenticated
    def patch(self, team_id):
        """
        修改俱乐部信息;
        俱乐部徽标额外接口修改
        """
        team = Team.get_or_404(id=team_id)
        self.has_update_permission(team)
        form = self.validated_arguments
        Team.update(**form).where(Team.id == team.id).execute()
        self.set_status(204)


@rest_app.route(r"/teams/(\d+)/icon")
class TeamIconUpdateHandler(BaseClubAPIHandler):
    """
    修改俱乐部徽标
    """

    def has_update_permission(self, team):
        """
        是否具有修改权限
        目前只有俱乐部所有者可以修改
        :param team: Team
        """
        # TODO: 俱乐部的管理员如果具有修改权限也可以修改
        if self.current_user == team.owner:
            return True
        raise ApiException(403, "无权修改俱乐部")

    @authenticated
    def put(self, team_id):
        team = Team.get_or_404(id=team_id)
        self.has_update_permission(team)

        if "icon" not in self.request.files:
            raise ApiException(400, "请选择文件")

        to_bucket = self.settings['qiniu_avatar_bucket']
        to_key = "team:%s%s" % (self.current_user.id, time.time())
        to_key = hashlib.md5(to_key.encode()).hexdigest()

        icon_key = self.upload_file("icon",
                                    to_bucket=to_bucket,
                                    to_key=to_key,
                                    )
        team.icon_key = icon_key
        team.save()

        updated = Team.get(id=team.id)
        self.write(updated.icon)


@rest_app.route(r'/teams/(\d+)/join')
class JoinTeamHandler(BaseClubAPIHandler):
    """加入俱乐部"""

    @validate_arguments_with(schema.join_team)
    @authenticated
    def post(self, team_id):
        form = self.validated_arguments
        team = Team.get_or_404(id=team_id)

        if team.is_member(user_id=self.current_user.id):
            raise ApiException(422, "你已是俱乐部会员, 不用重复加入")

        if team.open_type == 0:
            state = TeamMember.TeamMemberState.normal.value
            msg = "正常"
        elif team.open_type == 1:
            state = TeamMember.TeamMemberState.pending.value
            msg = "待审核"
        else:
            raise ApiException(422, "俱乐部拒绝加入")

        team.add_member(user_id=self.current_user.id,
                        role=Team.TeamRole.member,
                        state=state,
                        **form)
        self.write_success(msg=msg)


@rest_app.route(r'/teams/(\d+)/leave')
class LeaveTeamHandler(BaseClubAPIHandler):

    def get(self, team_id):
        team = Team.get_or_404(id=team_id)
        if not team.is_member(user_id=self.current_user.id):
            raise ApiException(400, "未加入俱乐部")

        team.leave(self.current_user)

        self.set_status(204)


class MemberFilter(Filter):

    group = StringFiltering(source='group_name')

    class Meta:
        fields = ("group",)


@rest_app.route(r'/teams/(\d+)/members')
class ListTeamMembers(BaseClubAPIHandler):
    """获取俱乐部成员"""

    login_required = False
    filter_classes = (MemberFilter,)

    @authenticated
    def get(self, team_id):
        """获取俱乐部成员列表"""

        query = TeamMember.select().where(TeamMember.team == team_id)
        query = self.filter_query(query)

        page = self.paginate_query(query)
        data = self.get_paginated_data(page, alias='members',
                                       serializer=SimpleMemberSerializer)
        self.write(data)


@rest_app.route(r'/teams/(\d+)/members/(\d+)')
class TeamMemberDetail(BaseClubAPIHandler):
    """获取会员详情"""

    @authenticated
    def get(self, team_id, user_id):
        team = Team.get_or_404(id=team_id)
        member = TeamMember.get_or_404(user=user_id, team=team_id)

        if self.current_user == member.user or self.current_user == team.owner:
            serializer = InsecureMemberSerializer
        else:
            serializer = SimpleMemberSerializer

        self.write(serializer(instance=member).data)

    def has_update_permission(self, member: TeamMember):
        members_team = member.team
        if self.current_user == member.user or \
                members_team.owner == self.current_user:
            return True
        raise ApiException(403, "没有修改会员的权限")

    def validate_group_id(self, team, group_id):
        """校验分组是否存在"""
        try:
            group = TeamMemberGroup.get(id=group_id, team=team)
        except TeamMemberGroup.DoesNotExist:
            logging.debug("{0} {1}".format(group_id, team.groups))
            raise ApiException(400, "分组不存在")

        return group

    @validate_arguments_with(schema.patch_member)
    @authenticated
    def patch(self, team_id, user_id):
        """修改会员信息, 如果有分组信息变化, 需要额外处理"""
        form = self.validated_arguments
        if not form:
            raise ApiException(400, "填写需要修改的属性和值")

        team = Team.get_or_404(id=team_id)
        member = TeamMember.get_or_404(user=user_id, team=team_id)

        self.has_update_permission(member)

        group = None
        group_id = form.pop("group_id", None)
        if group_id:
            group = self.validate_group_id(team, group_id)

        with self.db.transaction():

            # 如果有分组修改, 额外处理
            if group:
                TeamMemberGroupService.add_member(group, member)
                form["group_name"] = group.name

            logging.debug(form)
            TeamMember.update(**form)\
                .where(TeamMember.id == user_id, TeamMember.team == team_id)\
                .execute()

        self.set_status(204)


@rest_app.route(r"/teams/(\d+)/member_groups", name="rest_team_group")
class TeamMemberGroupHandler(BaseClubAPIHandler):
    """
    俱乐部分组列表
    """

    def has_read_permission(self, team):
        """具有俱乐部分组读取权限"""

        # TODO: 俱乐部管理员应该具有权限

        if self.current_user == team.owner:
            return True
        raise ApiException(403, "权限错误")

    @authenticated
    def get(self, team_id):
        """
        获取俱乐部分组
        Args:
            team_id: int

        """
        team = Team.get_or_404(id=team_id)
        self.has_read_permission(team)

        query = TeamMemberGroup.select().where(TeamMemberGroup.team == team)
        page = self.paginate_query(query)
        data = self.get_paginated_data(page=page, alias="groups")
        self.write(data)

    @validate_arguments_with(schema.create_group)
    @authenticated
    def post(self, team_id):
        """
        新建俱乐部分组
        Args:
            team_id:

        Returns:

        """
        team = Team.get_or_404(id=team_id)
        self.has_read_permission(team)
        form = self.validated_arguments

        group = TeamMemberGroup.create(team=team, **form)

        self.set_status(201)
        self.write(group.info)


@rest_app.route(r"/teams/(\d+)/member_groups/(\d+)")
class TeamMemberGroupObjectHandler(BaseClubAPIHandler):
    """
    俱乐部分组 object
    """

    def has_read_permission(self, team):
        if self.current_user == team.owner:
            return True
        raise ApiException(403, "权限错误")

    def has_delete_permission(self, team):
        if self.current_user == team.owner:
            return True
        raise ApiException(403, "权限错误, 没有删除分组的权限")

    @validate_arguments_with(schema.create_group)
    @authenticated
    def patch(self, team_id, group_id):
        """
        修改分组
        Args:
            team_id:
            group_id:

        Returns:

        """
        team = Team.get_or_404(id=team_id)
        TeamMemberGroup.get_or_404(id=group_id, team=team)

        self.has_read_permission(team)

        TeamMemberGroup\
            .update(**self.validated_arguments)\
            .where(TeamMemberGroup.team == team, TeamMemberGroup.id == group_id)\
            .execute()

        self.set_status(204)

    def group_allow_delete(self, group):
        if group.members.count() == 0:
            return True
        raise ApiException(409, "请先清空分组成员")

    @authenticated
    def delete(self, team_id, group_id):
        """
        删除分组
        Args:
            team_id:
            group_id:

        """
        team = Team.get_or_404(id=team_id)
        group = TeamMemberGroup.get_or_404(id=group_id, team=team)

        self.has_delete_permission(team)

        self.group_allow_delete(group)

        self.set_status(204)


@rest_app.route(r"/team/(\d+)/followers")
class FollowTeamHandler(BaseClubAPIHandler):
    """用户关注和取消关注俱乐部"""

    def get(self, team_id: int):
        """俱乐部粉丝列表"""
        team = Team.get_or_404(id=team_id)
        query = TeamService.followers(team=team)
        page = self.paginate_query(query)

        data = self.render_page_info(page)
        data["followers"] = []
        uids = set()

        def merge_followers(ids, parteam_users):
            for uid in ids:
                user = parteam_users[uid]
                data.setdefault("followers", []).append(user.secure_info)

        for row in page:
            uids.add(row.user_id)
        if uids:
            pt = Parteam(self.settings["parteam_api_url"])
            pt_users = pt.parteam_user(list(uids))
            merge_followers(uids, pt_users)

        self.write(data)

    @authenticated
    def post(self, team_id: int):
        """
        关注俱乐部
        :param team_id:
        :return:
        """
        team = Team.get_or_404(id=team_id)  # type: Team
        if team.get_follower(user_id=self.current_user.id):
            raise ApiException(422, "您已关注俱乐部, 无须重复关注")
        team.add_follower(user_id=self.current_user.id)
        self.set_status(204, "关注成功")

    @authenticated
    def delete(self, team_id: int):
        """
        取消关注
        :param team_id:
        :return:
        """
        # user_id = self.get_query_argument("user_id", None)
        user_id = self.current_user.id
        team = Team.get_or_404(id=team_id)  # type: Team
        if not team.get_follower(user_id=user_id):
            raise ApiException(422, "您未关注俱乐部")

        team.delete_follower(user_id=user_id)
        self.set_status(204, "取消关注成功")
