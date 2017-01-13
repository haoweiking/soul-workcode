import hashlib
import time

from yiyun import tasks
from yiyun.models import Team, ChinaCity, TeamCertifyApplication
from .base import ClubBaseHandler, club_app
from .forms.team import CreateTeamFrom, TeamCertifyApplicationForm


@club_app.route("/create", name="club_create")
class CreateHandler(ClubBaseHandler):
    """docstring for CreateHandler"""

    team_required = False
    email_verified_required = False

    def get(self):
        team = self.current_team
        if team is not None:
            if team.state == 1:
                return self.redirect(self.reverse_url("club_home"))
            else:
                return self.redirect(self.reverse_url("club_wait_approve"))

        form = CreateTeamFrom()

        province = form.province.choices[0][0]
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("club/create.html",
                    form=form,
                    cities=ChinaCity.get_cities())

    def post(self):

        team = self.current_team
        if team is None:
            team = Team(owner_id=self.current_user.id)

        form = CreateTeamFrom(self.arguments)

        if form.validate():
            form.populate_obj(team)
            team.owner_id = self.current_user.id
            team.sport = [str(n.id) for n in team.sport]

            if "iconfile" in self.request.files:
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "team:%s%s" % (self.current_user.id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                icon_key = self.upload_file("iconfile",
                                            to_bucket=to_bucket,
                                            to_key=to_key,
                                            )

                team.icon_key = icon_key

            team.save()

            # TODO: 正式版本需要移除此自动通过审核功能
            tasks.team.approve_team.apply_async((team.id, ), countdown=30)

            return self.redirect(self.reverse_url("club_wait_approve"))

        province = self.get_argument("province", None)
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("club/create.html",
                    form=form,
                    cities=ChinaCity.get_cities())


@club_app.route("/wait_approve", name="club_wait_approve")
class WaitApproveHandler(ClubBaseHandler):
    """docstring for WaitApproveHandler"""

    team_required = False
    email_verified_required = False

    def get(self):
        team = Team.get_or_none(owner_id=self.current_user.id)
        if team is None:
            return self.redirect(self.reverse_url("club_create"))
        elif team.state == 1:
            return self.redirect(self.reverse_url("club_home"))
        else:
            self.render("club/wait_approve.html")


@club_app.route("/info/basic", name="club_info_basic")
class BasicInfo(ClubBaseHandler):

    """
    展示俱乐部基本信息
    """

    def get(self):
        # 获取实名认证申请信息
        application =\
            TeamCertifyApplication.get_or_none(team_id=self.current_team.id)
        self.render("club/basic_info.html",
                    application=application,
                    team=self.current_team)


@club_app.route("/info/finance", name="club_info_finance")
class BasicFinanceInfo(ClubBaseHandler):

    """
    展示俱乐部基本财务信息
    """

    def get(self):
        settings = self.current_team.get_settings()
        self.render("club/finance_info.html",
                    settings=settings,
                    team=self.current_team)


@club_app.route("/certify/enterprise/create",
                name="club_certify_enterprise_create")
class CertifyEnterpriseCreate(ClubBaseHandler):

    """
    用户申请企业认证，或修改认证信息
    """

    def _upload_files(self, field_names_list):
        img_keys = []
        for field_name in field_names_list:
            to_bucket = self.settings["qiniu_file_bucket"]
            to_key = "certify:%s%s" % (self.current_team.id, time.time())
            to_key = hashlib.md5(to_key.encode()).hexdigest()

            cover_key = self.upload_file(field_name,
                                         to_bucket=to_bucket,
                                         to_key=to_key)
            img_keys.append(cover_key)

        return img_keys

    def get(self):
        application =\
            TeamCertifyApplication.get_or_none(team_id=self.current_team.id)

        if application is not None:
            # 存在申请记录
            if application.is_approved:
                # 已经审核通过
                self.redirect(self.reverse_url("club_info_basic"))
            else:
                # 其余情况 只能修改原有的申请记录
                form = TeamCertifyApplicationForm(obj=application)
        else:
            form = TeamCertifyApplicationForm()

        self.render("club/certify_enterprise.html",
                    application=application,
                    form=form)

    def post(self):
        application =\
            TeamCertifyApplication.get_or_none(team_id=self.current_team.id)

        form = TeamCertifyApplicationForm(self.arguments)

        if not form.validate():
            self.render("club/certify_enterprise.html",
                        application=application,
                        form=form)
        else:
            file_field_names_list = ["license_img_key",
                                     "director_id_card_front_side_img_key",
                                     "director_id_card_back_side_img_key"]

            if application is None:
                application = TeamCertifyApplication()

                # 判断图片完整性
                file_field_has_error = False
                for file_field_name in file_field_names_list:
                    field = getattr(form, file_field_name)
                    if not field.data:
                        field.errors = [("必填",)]
                        file_field_has_error = True

                if file_field_has_error:
                    return self.render("club/certify_enterprise.html",
                                       application=application,
                                       form=form)

            else:
                if application.is_approved:
                    # 已经审核通过
                    return self.redirect(self.reverse_url("club_info_basic"))
                else:
                    # TODO 修改了值 才能重新设置状态为 等待审核
                    # 修改状态为 等待审核
                    application.set_requesting()

                    # 过滤掉没有更新的文件
                    empty_file_field_names_list = []
                    for file_field_name in file_field_names_list:
                        field = getattr(form, file_field_name)
                        if not field.data:
                            empty_file_field_names_list.append(file_field_name)

                    for file_field_name in empty_file_field_names_list:
                        # 从 form 中删除，否则没有选择的文件 field 会被重写为空
                        delattr(form, file_field_name)
                        file_field_names_list.remove(file_field_name)

            form.populate_obj(application)
            application.team_id = self.current_team.id

            img_keys = self._upload_files(file_field_names_list)
            for index, field_name in enumerate(file_field_names_list):
                setattr(application, field_name, img_keys[index])

            application.save()
            self.redirect(self.reverse_url("club_info_basic"))
