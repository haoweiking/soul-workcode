import hashlib
from datetime import datetime
from collections import OrderedDict

from .base import BaseModel

from peewee import (BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured)

from yiyun.helpers import create_token
from yiyun.ext.cache import cached_property
from yiyun.ext.database import ListField, PasswordField


class Admin(BaseModel):

    class Meta:
        db_table = 'admin'

    ROLES_ADMIN = "admin"
    ROLES_MARKETING = "marketing"

    ROLES = [
        (ROLES_ADMIN, "后台管理"),
        (ROLES_MARKETING, "运营管理")
    ]

    username = CharField(max_length=32, unique=True, verbose_name="用户名")
    password = PasswordField(max_length=128, verbose_name="登录密码")
    password_changed = DateTimeField(default=datetime.now)

    mobile = CharField(
        null=True, max_length=15, index=True, verbose_name="手机号")
    email = CharField(
        null=True, index=True, max_length=128, verbose_name="电子邮箱")

    qq = CharField(default="", verbose_name="QQ 号码")
    weixin = CharField(default="", verbose_name="微信帐号")

    name = CharField(max_length=64, default="", verbose_name="姓名")
    gender = CharField(max_length=1, default="n", verbose_name="性别", choices=[
                       ('m', '男'), ('f', '女'), ('n', '保密')])

    login_times = IntegerField(default=0)
    last_login = DateTimeField(default=None, null=True)
    last_ip = CharField(max_length=15, default="")

    is_super = BooleanField(default=False, verbose_name="超级管理员", db_column="is_superadmin")
    roles = ListField(default=[], choices=ROLES, verbose_name="权限")

    state = IntegerField(
        default=1, verbose_name="状态", choices=[(1, '可用'), (0, '禁止')])

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)

    # role 仅为 运营管理的 admin, 会受到地域的限制
    manage_provinces = ListField(default=[], verbose_name="可以管辖的省份列表")

    @staticmethod
    def create_password(raw):
        salt = create_token(8)
        passwd = '%s%s%s' % (salt, raw, 'yiyun')
        hsh = hashlib.sha1(passwd.encode("utf-8")).hexdigest()
        return "%s$%s" % (salt, hsh)

    @staticmethod
    def check_password(passwd, raw):
        if not passwd or '$' not in passwd:
            return False
        salt, hsh = passwd.split('$', 1)
        new_passwd = '%s%s%s' % (salt, raw, 'yiyun')
        new_passwd = new_passwd.encode("utf-8")
        verify = hashlib.sha1(new_passwd).hexdigest()
        return verify == hsh

    @property
    def state_name(self):
        if self.state == 0:
            return "禁止"

        elif self.state == 1:
            return "可用"

        return "未知"

    @property
    def role_names(self):
        names = []
        for role in self.roles:
            names.append(Admin.get_role_name(role))

        return names

    @property
    @cached_property
    def mini_info(self):
        if not hasattr(self, '_mini_info'):
            self._mini_info = self.to_json(
                only=[Admin.id, Admin.name]
            )

        return self._mini_info

    @classmethod
    def get_role_name(cls, role):
        roles = OrderedDict(cls.ROLES)
        return roles.get(role, "未知")

    def is_role(self, role):
        return role in self.roles

    @property
    def valid_manage_provinces(self):
        """
        排除空列表的请款
        Returns:
        """

        if len(self.manage_provinces) > 0:
            return self.manage_provinces
        else:
            return [""]

    def is_restrict_by_areas(self):
        """
        当前管理员是否受到地域限制
        现在的逻辑是: 非超管而且 role 仅仅是 'marketing' 的才受限制
        """

        if self.is_super:
            return False

        # role　中包括　marketing
        if self.ROLES_MARKETING in self.roles:
            # 仅有一个 role
            if len(self.roles) == 1:
                return True
            else:
                return False
        else:
            return False

    @classmethod
    def get_all(cls):

        query = Admin.select()

        admins = {}
        for admin in query:
            admins[admin.id] = admin

        return admins


class AdminRole(BaseModel):

    class Meta:
        db_table = 'admin_role'
        indexes = (
            (('admin_id', 'role'), True),
        )

    admin_id = IntegerField()
    role = CharField(max_length=64)
    permissions = ListField(default=[])

    operator_id = IntegerField(default=0)

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)


class AdminLog(BaseModel):

    """docstring for AdminLog"""

    class Meta:
        db_table = 'admin_log'

    admin_id = IntegerField()
    ip = CharField(max_length=15, default="")
    action = CharField()
    descprition = CharField()

    time = DateTimeField(default=datetime.now)


class Announce(BaseModel):
    """docstring for announce"""

    title = CharField()
    content_type = CharField(default="text")
    content = TextField()

    author = ForeignKeyField(Admin)

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
