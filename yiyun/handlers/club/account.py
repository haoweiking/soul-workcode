import time
import hashlib
from datetime import datetime

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile
from yiyun.models import User

from wtforms import ValidationError
from .forms.account import (ProfileFrom, ChangePasswordForm,
                            ChangeMobileForm, ChangeEmailForm)


class AccountBaseHandler(ClubBaseHandler):

    def validate_password(self, form):
        password = self.get_argument("password")

        if not User.check_password(self.current_user.password, password):
            form.password.errors = [ValidationError("旧密码不正确")]
            return False

        return True


@club_app.route("/account/profile", name="club_account_profile")
class ProfileHandler(AccountBaseHandler):

    def get(self):
        form = ProfileFrom(obj=self.current_user)
        self.render("account/profile.html", form=form)

    def post(self):
        form = ProfileFrom(self.arguments, obj=self.current_user)

        if form.validate():
            user = self.current_user
            form.populate_obj(user)
            user.updated = datetime.now()

            if "avatarfile" in self.request.files:
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "user:%s%s" % (self.current_user.id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                avatar_key = self.upload_file("avatarfile",
                                              to_bucket=to_bucket,
                                              to_key=to_key,
                                              )

                user.avatar_key = avatar_key

            user.save()

            self.flash("修改基本资料成功！", category='success')
            self.redirect(self.reverse_url("club_account_profile"))
            return

        self.render("account/profile.html", form=form)


@club_app.route("/account/change_password", name="club_account_change_password")
class PasswordHandler(AccountBaseHandler):

    def get(self):
        form = ChangePasswordForm()
        self.render("account/change_password.html", form=form)

    def post(self):
        form = ChangePasswordForm(self.arguments)

        if form.validate() and self.validate_password(form):

            User.update(
                password=User.create_password(self.get_argument("newPassword"))
            ).where(
                User.id == self.current_user.id
            ).execute()

            self.flash("修改密码成功！", category='success')
            self.redirect(self.reverse_url("club_account_change_password"))
            return

        self.render("account/change_password.html", form=form)


@club_app.route("/account/change_mobile", name="club_account_change_mobile")
class ChangeMobileHandler(AccountBaseHandler):

    def get(self):
        form = ChangeMobileForm()
        self.render("account/change_mobile.html", form=form)

    def validate_password(self, form):
        password = self.get_argument("password")
        if not password or \
                not User.check_password(self.current_user.password, password):
            form.password.errors = [ValidationError("旧密码不正确")]
            return False

        return True

    def validate_mobile(self, form):
        mobile = self.get_argument("mobile")
        verify_code = self.get_argument("verify_code")

        if not self.verify_mobile(mobile, verify_code):
            form.verify_code.errors = [ValidationError("验证码不正确")]
            return False

        if User.select().where(
            (User.mobile == mobile
             ) & (User.id != self.current_user.id)
        ).exists():
            form.mobile.errors = [ValidationError("手机号已存在")]
            return False

        return True

    def post(self):
        form = ChangeMobileForm(self.arguments)

        if form.validate() \
                and self.validate_password(form) \
                and self.validate_mobile(form):

            User.update(
                mobile=self.get_argument("mobile")
            ).where(
                User.id == self.current_user.id
            ).execute()

            self.flash("修改手机号成功！", category='success')
            self.redirect(self.reverse_url("club_change_mobile"))
            return

        self.validate_password(form)

        self.render("account/change_mobile.html", form=form)


@club_app.route("/account/change_email", name="club_account_change_email")
class ChangeEmailHandler(AccountBaseHandler):

    def get(self):
        form = ChangeEmailForm()
        self.render("account/change_email.html", form=form)

    def post(self):
        form = ChangeEmailForm(self.arguments)

        if form.validate() and self.validate_password(form)\
                and self.validate_email_existed(form):
            self.current_user.email = form.new_email.data
            self.current_user.save()

            return self.redirect(self.reverse_url("club_account_change_email"))

        self.render("account/change_email.html", form=form)

    @staticmethod
    def validate_email_existed(form):
        user = User.get_or_none(email=form.new_email.data)
        if user:
            form.new_email.errors.append('邮箱已存在')
            return False
        else:
            return True
