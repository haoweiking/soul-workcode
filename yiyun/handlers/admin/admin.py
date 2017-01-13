import tornado
import logging
import hashlib
import time
from datetime import datetime

from wtforms import ValidationError

from yiyun.models import Admin
from yiyun.helpers import intval
from .base import AdminBaseHandler, admin_app
from .forms.admin import CreateAdminForm, EditAdminForm


@admin_app.route(r'/admins', name="admin_admins")
class AdminsHandler(AdminBaseHandler):

    def get(self):
        keyword = self.get_argument("kw", "")

        query = Admin.select()
        if keyword:
            query = query.where(
                (Admin.name.contains(keyword)
                 ) | (Admin.username.contains(keyword)
                      ) | (Admin.email.contains(keyword)
                           ) | (Admin.mobile == keyword)
            )

        query = query.order_by(Admin.id.asc())

        admins = self.paginate_query(query)

        self.render("admin/list.html",
                    admins=admins
                    )


@admin_app.route(r"/admins/(add|edit)", name="admin_admins_edit")
class AdminsEdit(AdminBaseHandler):
    """docstring for Admins"""

    def get(self, action):

        # 只有超级管理员可以修改管理员信息
        if not self.current_user.is_super:
            self.redirect(self.reverse_url("admin_admins"))

        if action == "add":
            admin = Admin()
            form = CreateAdminForm(obj=admin)
        else:
            admin = Admin.get_or_404(id=self.get_argument("id"))
            form = EditAdminForm(obj=admin)

        self.render("admin/form.html",
                    form=form,
                    admin=admin,
                    action=action)

    def validate_is_super(self, form, action, admin):

        if action == "add":
            return True

        if admin.id == self.current_user.id \
                and intval(self.get_argument("state", 0)) != 1:
            form.state.errors = [ValidationError("不能禁用自己"), ]

            return False

        return True

    def post(self, action):

        # 只有超级管理员可以修改管理员信息
        if not self.current_user.is_super:
            raise tornado.web.HTTPError(403)

        if action == "add":
            admin = Admin()
            form = CreateAdminForm(self.arguments, obj=admin)
        else:
            admin = Admin.get_or_404(id=self.get_argument("id"))
            form = EditAdminForm(self.arguments, obj=admin)

        if form.validate() and self.validate_is_super(form, action, admin):
            self.logger.debug(form.manage_provinces.data)
            form.populate_obj(admin)

            if action == "add":
                admin.password = Admin.create_password(admin.password)

            elif action == "edit" and self.get_argument("newpassword", None):
                admin.password = Admin.create_password(
                    self.get_argument("newpassword", None))
                admin.password_changed = datetime.now()

            admin.email = admin.email if admin.email else None
            admin.save()

            if action == "add":
                self.flash("添加管理员成功", category="success")
            else:
                self.flash("修改管理员成功", category="success")

            self.redirect(self.reverse_url('admin_admins'))
            return

        self.validate_is_super(form, action, admin)

        self.render("admin/form.html",
                    form=form,
                    admin=admin,
                    action=action)
