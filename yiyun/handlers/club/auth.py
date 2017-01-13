import io
import os
import random
from datetime import datetime
from urllib import parse
from urllib.parse import urljoin

import tornado.escape
from wtforms import ValidationError

from yiyun import tasks
from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile, intval, is_email
from yiyun.libs.captcha import create_captcha
from yiyun.models import User, Team, ChinaCity
from .base import ClubBaseHandler, club_app
from .forms.users import RegisterForm, LoginForm, MobileResetPasswordForm,\
    LoginVerifyCodeForm, EmailResetPasswordForm


class HandlerCaptchaMixin(object):

    @classmethod
    def get_captcha_cache_key(cls, session_id: str):
        key_template = "club:auth:captcha:{session_id}"
        return key_template.format(session_id=session_id)

    @classmethod
    def verify_captcha(cls, cache_engine, session_id: str, value: str):
        key = cls.get_captcha_cache_key(session_id)
        captcha_value = cache_engine.get(key)  # type: str
        return captcha_value == value.strip().lower()


class HandlerMailMixin(object):

    @classmethod
    def get_verify_mail_cache_key(cls, email: str):
        key_template = "club:auth:email:verify_code:{email}"
        return key_template.format(email=email)

    @classmethod
    def get_reset_password_mail_cache_key(cls, email: str):
        key_template = "club:auth:email:reset_code:{email}"
        return key_template.format(email=email)


@club_app.route(r"/auth/captcha.jpg", name="club_captcha_image")
class HandlerCaptchaImage(HandlerCaptchaMixin, ClubBaseHandler):

    login_required = False
    team_required = False
    email_verified_required = False

    def get(self):

        image, chars = create_captcha()

        cache_key = self.get_captcha_cache_key(self.session_id)

        self.redis.set(cache_key, "".join(chars).lower(), ex=300)

        o = io.BytesIO()
        image.save(o, format="JPEG")
        s = o.getvalue()
        o.close()

        self.set_header('Expires', '0')
        self.set_header(
            'Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))
        self.write(s)


@club_app.route("/auth/request_verify_code", name="club_request_verify_code")
class RequestVerifyCode(ClubBaseHandler):

    """请求发送短信验证码
        根据 action 发送不同目的的验证码
    """

    login_required = False
    team_required = False
    email_verified_required = False

    def post(self):

        mobile = self.get_argument("mobile")
        action = self.get_argument("action")

        if not is_mobile(mobile):
            raise ArgumentError(400, "手机号码格式不正确")

        sent_times_key = "yiyun:mobile:%s:code_sent_times" % mobile
        if intval(self.redis.get(sent_times_key)) >= 5:
            raise ArgumentError(400, "你已重发5次，请稍后再试")

        # 有效期内发送相同的验证码
        verify_code = random.randint(1000, 9999)
        is_registered = User.select().where(User.mobile == mobile).exists()
        self.logger.debug("send: %s to %s" % (verify_code, mobile))

        if action == "register" and is_registered:
            raise ArgumentError(1020, "手机号码已注册", status_code=400)

        if action in ('register_or_login', 'register', 'login'):
            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            tasks.message.send_sms_verifycode(mobile, verify_code)

            self.write_success(is_registered=is_registered)

        elif action == "forgot":

            if not is_registered:
                raise ArgumentError(400, "手机号码没有注册")

            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            tasks.message.send_sms_verifycode(mobile, verify_code)

            self.write_success()

        elif action == "update_mobile":
            if not self.current_user:
                raise ArgumentError(403, "登录后才能修改手机号")

            if is_registered:
                raise ArgumentError(403, "该号码已经使用，请更换")

            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            tasks.message.send_sms_verifycode(mobile, verify_code)

            # 关联验证码与当前用户
            self.redis.set("ihealth:update_mobile:%s:verify_code:%s" % (
                mobile, verify_code), self.current_user.id)

            # 30分钟内有效
            self.redis.expire(
                "ihealth:update_mobile:%s:verify_code:%s" % (
                    mobile, verify_code), 1800)

            self.write_success()

        # 30分钟内最多发送5次验证码
        sent_times = int(self.redis.incr(sent_times_key))
        if sent_times == 1:
            self.redis.expire(sent_times_key, 1800)


# Email part


@club_app.route("/auth/verify_email", name="club_verify_email")
class VerifyEmail(HandlerMailMixin, ClubBaseHandler):

    """使用验证码验证邮箱
    """

    login_required = True
    team_required = False
    email_verified_required = False

    def get(self):
        verify_code = self.get_argument("code", "")

        key = self.get_verify_mail_cache_key(self.current_user.email)

        code = self.redis.get(key)
        if code and verify_code != code:
            success = False
        else:
            self.current_user.email_verified = True
            self.current_user.save()
            success = True

        self.render("email/email_verify.html",
                    success=success)


@club_app.route("/auth/request_verify_email", name="club_request_verify_email")
class RequestVerifyEmail(HandlerMailMixin, ClubBaseHandler):

    """请求发送邮箱验证码
    """

    login_required = True
    team_required = False
    email_verified_required = False

    def get(self):
        if self.current_user.email_verified:
            message = "邮箱已验证，无需重复验证"
        else:
            key = self.get_verify_mail_cache_key(self.current_user.email)
            verify_code = random.randint(1000, 9999)

            # 验证码两小时内有效
            self.redis.set(key, verify_code)
            self.redis.expire(key, 3600 * 2)

            name = self.current_user.name or self.current_user.email

            # 发送验证邮件
            verify_url = urljoin(self.request.full_url(),
                                 self.reverse_url('club_verify_email'))

            tasks.user.send_verify_email.delay(
                name, self.current_user.email,
                verify_code, verify_url=verify_url)
            message = "验证邮件已发送，请登陆邮箱查看"

        self.write_success(message=message)


@club_app.route("/auth/wait_email_verify",
                name="club_wait_email_verify")
class WaitEmailVerify(ClubBaseHandler):
    login_required = True
    team_required = False
    email_verified_required = False

    def get(self):
        if self.current_user.email_verified:
            return self.redirect(self.reverse_url("club_home"))
        self.render("email/wait_email_verify.html")


######################


class AuthBaseHandler(HandlerCaptchaMixin, ClubBaseHandler):
    """docstring for AuthBaseHandler"""

    login_required = False
    team_required = False
    email_verified_required = False

    @classmethod
    def have_user(cls, name: str) -> User:
        """
        检查用户是否存在，如果存在返回用户实例，否则返回None
        Args:
            name: email or mobile
        """
        if is_mobile(name):
            data = {"mobile": name}
        elif is_email(name):
            data = {"email": name}
        else:
            return None
        return User.get_or_none(**data)

    def login(self, user: User, expires_days: int=None):
        self.set_secure_cookie("club_session",
                               tornado.escape.json_encode({
                                   "id": user.id,
                               }), expires_days=expires_days)

        User.update(
            last_login=datetime.now()
        ).where(
            User.id == user.id
        ).execute()


@club_app.route("/login", name="club_auth_login")
class LoginHandler(AuthBaseHandler):
    """docstring for LoginHandler"""

    def get(self):
        form = LoginForm()
        messages = self.get_flashed_messages()
        self.render("login_new.html", form=form, messages=messages)

    def post(self):
        form = LoginForm(self.arguments)

        if form.validate():
            user = self.have_user(form.username.data)
            if user and User.check_password(user.password,
                                            form.password.data):

                remember_me = self.get_argument("remember", "off")

                if remember_me == "on":
                    expires_days = 30
                else:
                    expires_days = None

                self.login(user, expires_days)

                team = Team.get_or_none(owner_id=user.id)
                if team is None:
                    return self.redirect(self.reverse_url("club_create"))
                elif team.state == 0:
                    return self.redirect(self.reverse_url("club_wait_approve"))
                elif self.next_url:
                    return self.redirect(self.next_url)
                else:
                    return self.redirect(self.reverse_url("club_home"))

        messages = [('danger', '登录失败：账号或密码不正确')]
        self.render("login.html", form=form, messages=messages)


@club_app.route("/login_verify_code", name="club_auth_login_verify_code")
class LoginVerifyCodeHandler(AuthBaseHandler):
    """docstring for LoginHandler"""

    def get(self):
        form = LoginVerifyCodeForm()
        self.render("login-by-sms.html", form=form, fail=False)

    def validate_verify_code(self, form):
        verify_code = self.get_argument("verify_code")
        mobile = self.get_argument("mobile")

        if not self.verify_mobile(mobile, verify_code):
            form.verify_code.errors = [ValidationError("验证码错误")]
            return False

        return True

    def post(self):
        form = LoginVerifyCodeForm(self.arguments)

        fail = False
        if form.validate() and self.validate_verify_code(form):
            user = User.get_or_none(mobile=self.get_argument("mobile"))
            if user:
                remember_me = self.get_argument("remember", "off")

                if remember_me == "on":
                    expires_days = 30
                else:
                    expires_days = None

                self.login(user, expires_days)

                team = Team.get_or_none(owner_id=user.id)
                if team is None:
                    self.redirect(self.reverse_url("club_create"))
                    return

                if team.state == 0:
                    self.redirect(self.reverse_url("club_wait_approve"))
                    return

                if self.next_url:
                    self.redirect(self.next_url)
                else:
                    self.redirect(self.reverse_url("club_home"))

                return

            fail = True

        self.render("login-by-sms.html", form=form, fail=fail)


@club_app.route("/logout", name="club_auth_logout")
class LogoutHandler(AuthBaseHandler):
    """docstring for LogoutHandler"""

    def get(self):
        self.clear_cookie("club_session")
        self.redirect(self.reverse_url("club_auth_login"))


@club_app.route("/register", name="club_auth_register")
class RegisterHandler(AuthBaseHandler):
    """docstring for RegisterHandler"""

    def get(self):
        form = RegisterForm()
        self.render("register.html", form=form)

    def post(self):

        form = RegisterForm(self.arguments)

        if form.validate() and self.verify_register_form_data(form):
            user = User()
            form.populate_obj(user)
            user.password = User.create_password(user.password)
            user.save()

            self.login(user)
            self.redirect(self.reverse_url("club_create"))
        else:
            self.render("register.html", form=form)

    def verify_register_form_data(self, form: RegisterForm):
        state = True
        if not self.verify_captcha(self.redis,
                                   self.session_id,
                                   form.captcha.data):
            form.captcha.errors.append('验证码错误')
            state = False
        if self.have_user(form.email.data):
            form.email.errors.append("此邮箱已注册")
            state = False
        return state

#  Reset Password


@club_app.route("/forgot_password", name="club_forgot_password")
class ForgotPasswordHandler(AuthBaseHandler):
    """
    选择重置密码方式页面(手机，邮箱)
    """

    def get(self):
        self.render("password/forgot_password.html")


@club_app.route("/mobile_reset_password", name="club_mobile_reset_password")
class MobileResetPassword(AuthBaseHandler):
    """docstring for ForgotPasswordHandler"""

    def get(self):
        form = MobileResetPasswordForm()
        self.render("password/mobile_reset_password.html", form=form)

    def validate_verify_code(self, form):
        verify_code = self.get_argument("verify_code")
        mobile = self.get_argument("mobile")

        if not self.verify_mobile(mobile, verify_code):
            form.verify_code.errors = [ValidationError("验证码错误")]
            return False

        return True

    def post(self):
        form = MobileResetPasswordForm(self.arguments)

        if form.validate() and self.validate_verify_code(form):
            User.update(
                password=User.create_password(self.get_argument("password"))
            ).where(
                User.mobile == self.get_argument("mobile")
            ).execute()

            self.flash("重置密码成功，请使用新密码登录")
            self.redirect(self.reverse_url("club_auth_login"))

        self.render("password/mobile_reset_password.html", form=form)


@club_app.route("/reset_password_email", name="club_reset_password_email")
class SendResetPasswordEmail(HandlerMailMixin, AuthBaseHandler):

    def get(self):
        self.render("password/reset_password_email.html")

    def post(self):
        email = self.get_argument("email", "")
        user = self.have_user(email)
        if user:
            key = self.get_reset_password_mail_cache_key(email)
            verify_code = random.randint(1000, 9999)

            # 验证码两小时内有效
            self.redis.set(key, verify_code)
            self.redis.expire(key, 3600 * 2)

            # 发送验证邮件
            verify_url = urljoin(self.request.full_url(),
                                 self.reverse_url('club_reset_password'))

            tasks.user.send_forgot_email.delay(
                user.name, email,
                verify_code, verify_url=verify_url)
            messages = [("info", "重置密码邮件已发送，请登陆邮箱查看")]
        else:
            messages = [("danger", "此邮箱未注册")]

        self.render("password/reset_password_email.html",
                    messages=messages)


@club_app.route(r"/reset_password", name="club_reset_password")
class ResetPasswordHandler(HandlerMailMixin, AuthBaseHandler):

    def get(self):
        email = self.get_argument("email", "")
        code = self.get_argument("code", "")
        form = EmailResetPasswordForm()
        form.email.data = email
        form.verify_code.data = code
        self.render("password/reset_password.html", form=form)

    def post(self):
        form = EmailResetPasswordForm(self.arguments)
        messages = self.get_flashed_messages()

        if form.validate():
            user = self.have_user(form.email.data)
            key = self.get_reset_password_mail_cache_key(form.email.data)
            verify_code = self.redis.get(key)
            if not user:
                messages = [('danger', '邮箱未注册')]
            elif not verify_code or verify_code != form.verify_code.data:
                messages = [('danger', '重置密码邮箱验证失败，请重新验证')]
            else:
                user.password = User.create_password(form.new_password.data)
                user.save()
                self.redis.delete(key)
                messages = [('info', '密码修改成功')]
                return self.redirect(self.reverse_url('club_auth_login'))

        self.render("password/reset_password.html",
                    form=form, messages=messages)


####################################
