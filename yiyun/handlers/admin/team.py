import logging
import hashlib
import time
from datetime import datetime

from yiyun.models import (Team, TeamMember, TeamMemberGroup, User,
                          TeamCertifyApplication)
from yiyun.helpers import intval
from .base import AdminBaseHandler, admin_app
from yiyun.exceptions import ArgumentError


@admin_app.route(r'/teams', name="admin_teams")
class TeamsHandler(AdminBaseHandler):

    def get(self):
        """获取俱乐部列表"""

        keyword = self.get_argument("kw", "")
        state = intval(self.get_argument("state", -1))
        sort = intval(self.get_argument("sort", 0))

        query = Team.select()

        # 这里限制的需要是 俱乐部创建者所在的位置进行过滤 而不是俱乐部本身的位置
        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.join(
                User,
                on=(User.id == Team.owner_id)
            ).where(
                User.province << self.current_user.valid_manage_provinces
            )

        if state in (0, 1):
            query = query.where(Team.state == state)

        if keyword:
            query = query.where(Team.name.contains(keyword))

        query = query.order_by(Team.id.desc())
        teams = self.paginate_query(query)

        self.render("team/list.html",
                    teams=teams,
                    )

    def post(self):

        action = self.get_argument("action")
        team_id = self.get_argument("team_id")

        if action == "pass":
            Team.update(
                state=1,
                updated=datetime.now()
            ).where(
                Team.id == team_id
            ).execute()

        self.write_success()


@admin_app.route(r"/teams/certify_applications",
                 name="admin_teams_certify_applications")
class TeamsCertifyApplications(AdminBaseHandler):

    """
    俱乐部的实名认证申请列表
    """

    def get(self):
        query = TeamCertifyApplication.select(
            TeamCertifyApplication,
            Team,
        ).join(
            Team,
            on=(Team.id == TeamCertifyApplication.team_id).alias("team")
        ).order_by(
            TeamCertifyApplication.created.desc()
        )

        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.join(
                User,
                on=(User.id == Team.owner_id)
            ).where(
                User.province << self.current_user.valid_manage_provinces
            )

        query = self.paginate_query(query)

        self.render("team/certify_applications.html",
                    applications=query)


@admin_app.route(r"/teams/certify_applications/action",
                 name="admin_teams_certify_applications_action")
class TeamsCertifyApplicationsAction(AdminBaseHandler):

    """
    俱乐部实名申请列表操作
    """

    def _approve(self, application_id):
        application = TeamCertifyApplication.get_or_404(id=application_id)
        team = Team.get_or_404(id=application.team_id)

        with(self.db.transaction()):
            application.set_approved()
            application.save()

            team.verified = True
            team.save()

        self.write_success()

    def _disapprove(self, application_id, reason=""):
        application = TeamCertifyApplication.get_or_404(id=application_id)
        team = Team.get_or_404(id=application.team_id)

        with(self.db.transaction()):
            application.set_disapproved()
            application.save()

            team.verified = False
            team.verified_reason = reason
            team.save()

        self.write_success()

    def post(self):
        action = self.get_argument("action", "")
        id = self.get_argument("id", "")

        if action == "approve":
            self._approve(id)
        elif action == "disapprove":
            reason = self.get_argument("reason")
            self._disapprove(id, reason)
        else:
            self.logger.error("用户在俱乐部实名认证申请列使用了不支持的操作: %s" % action)
            raise ArgumentError(400, "action: %s 不存在" % action)
