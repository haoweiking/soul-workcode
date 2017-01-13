import time
import hashlib

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile
from yiyun.models import Sport, Team, TeamSettings, ChinaCity

from .forms.settings import TeamBasicFrom, TeamMemberForm, TeamFinanceForm, \
    TeamWeixinForm


@club_app.route("/settings/basic", name="club_settings_basic")
class BasicSettings(ClubBaseHandler):

    def get(self):

        team = self.current_team
        if team.sport:
            team.sport = [s for s in Sport.select().where(Sport.id << team.sport)]

        form = TeamBasicFrom(obj=team)

        province = self.current_team.province
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("settings/basic.html",
                    form=form,
                    cities=ChinaCity.get_cities()
                    )

    def post(self):

        form = TeamBasicFrom(self.arguments)

        if form.validate():
            team = self.current_team
            form.populate_obj(team)
            team.sport = [str(s.id) for s in team.sport]

            if "iconfile" in self.request.files:
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "team:%s%s" % (self.current_user.id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                icon_key = self.upload_file("iconfile",
                                            to_bucket=to_bucket,
                                            to_key=to_key,
                                            )

                if icon_key:
                    team.icon_key = icon_key

            team.save()

            self.flash("修改俱乐部资料成功！", category='success')
            self.redirect(self.reverse_url("club_settings_basic"))
            return

        province = self.current_team.province
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("settings/basic.html",
                    form=form,
                    cities=ChinaCity.get_cities()
                    )


@club_app.route("/settings/member", name="club_settings_member")
class MemberSettings(ClubBaseHandler):

    def get(self):

        form = TeamMemberForm(obj=self.current_team)

        self.render("settings/member.html",
                    form=form)

    def post(self):

        form = TeamMemberForm(self.arguments, obj=self.current_team)

        if form.validate():
            team = self.current_team
            form.populate_obj(team)

            team.save()

            self.flash("修改俱乐部资料成功！", category='success')
            self.redirect(self.reverse_url("club_settings_member"))
            return

        self.render("settings/member.html",
                    form=form
                    )


@club_app.route("/settings/finance", name="club_settings_finance")
class FinanceSettings(ClubBaseHandler):

    def get(self):
        settings = self.current_team.get_settings()
        form = TeamFinanceForm(obj=settings)

        # 赛事主办不需要充值
        if self.current_team.type == 1:
            del form.recharge_enabled
            del form.default_credit_limit

        self.render("settings/finance.html",
                    form=form
                    )

    def post(self):

        settings = self.current_team.get_settings()
        form = TeamFinanceForm(self.arguments, obj=settings)

        if self.current_team.type == 1:
            del form.recharge_enabled
            del form.default_credit_limit

        if form.validate():
            form.populate_obj(settings)
            settings.save()

            self.flash("修改财务设置成功！", category='success')
            self.redirect(self.reverse_url("club_settings_finance"))
            return

        self.render("settings/finance.html",
                    form=form
                    )


@club_app.route("/settings/mini_site", name="club_settings_mini_site")
class MiniSiteSettings(ClubBaseHandler):

    def get(self):

        self.render("settings/mini_site.html",
                    base_url=self.settings['club_url']
                    )
