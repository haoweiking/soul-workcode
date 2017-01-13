import random
from datetime import datetime
import io
import tornado.escape

from .base import AdminBaseHandler, admin_app
from wtforms import ValidationError

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile, intval
from yiyun.models import Admin, Team
from yiyun.libs.captcha import create_captcha
from yiyun import tasks
from .forms.auth import LoginFrom


@admin_app.route(r"/auth/captcha.jpg", name="admin_captcha_image")
class CaptchaImage(AdminBaseHandler):

    login_required = False

    def get(self):

        image, chars = create_captcha()

        self.redis.set("admin:auth:captcha:%s" % self.session_id, "".join(chars).lower(), ex=300)

        o = io.BytesIO()
        image.save(o, format="JPEG")

        s = o.getvalue()

        self.set_header('Expires', '0')
        self.set_header(
            'Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))
        self.write(s)


class AuthBaseHandler(AdminBaseHandler):
    """docstring for AuthBaseHandler"""

    login_required = False

    def login(self, admin, expires_days=None):
        self.set_secure_cookie("admin",
                               tornado.escape.json_encode({
                                   "id": admin.id,
                                   "username": admin.username
                               }), expires_days=expires_days)

        Admin.update(
            last_login=datetime.now()
        ).where(
            Admin.id == admin.id
        ).execute()


@admin_app.route("/login", name="admin_auth_login")
class LoginHandler(AuthBaseHandler):
    """docstring for LoginHandler"""

    def get(self):
        form = LoginFrom()
        self.render("login.html", form=form, fail=False)

    def post(self):
        form = LoginFrom(self.arguments)

        fail = False
        if form.validate():
            admin = Admin.get_or_none(username=self.get_argument("username"))
            if admin and Admin.check_password(admin.password,
                                            self.get_argument("password")):

                remember_me = self.get_argument("remember", "off")

                if remember_me == "on":
                    expires_days = 30
                else:
                    expires_days = None

                self.login(admin, expires_days)

                if self.next_url:
                    self.redirect(self.next_url)
                else:
                    self.redirect(self.reverse_url("admin_home"))

                return

        fail = True

        self.render("login.html", form=form, fail=fail)


@admin_app.route("/logout", name="admin_auth_logout")
class LogoutHandler(AuthBaseHandler):
    """docstring for LogoutHandler"""

    def get(self):
        self.clear_cookie("admin")
        self.redirect(self.reverse_url("admin_auth_login"))
