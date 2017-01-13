import hashlib
import time
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

import jwt
from cached_property import cached_property
from peewee import (CharField, DateTimeField,
                    IntegerField, BooleanField,
                    FloatField, DecimalField, DateField)

from yiyun.core import current_app as app
from yiyun.ext.database import JSONTextField
from yiyun.helpers import create_token
from .base import BaseModel


class Device(BaseModel):
    pass


class User(BaseModel):

    """用户"""

    class Meta:
        db_table = 'user'

    class UserGender(Enum):
        male = "m"
        female = "f"
        unknow = "n"

    GENDERS = {
        UserGender.unknow.value: "保密",
        UserGender.female.value: "女",
        UserGender.male.value: "男"
    }

    STATE_NAMES = {
        0: "禁止",
        1: "正常"
    }

    mobile = CharField(unique=True, max_length=15, null=True,
                       default=None, index=True, verbose_name="电话")

    email = CharField(unique=True, max_length=128, null=True,
                      default=None, index=True, verbose_name="邮箱")
    email_verified = BooleanField(default=False, verbose_name="邮箱是否验证")

    password = CharField(max_length=128, null=True, verbose_name="密码")

    name = CharField(max_length=64, default="", verbose_name="昵称")
    signature = CharField(default="", max_length=250, verbose_name="个性签名")
    gender = CharField(max_length=1, default=UserGender.unknow.value,
                       verbose_name="性别",
                       choices=(("n", "保密"), ("m", "男"), ("f", "女"))
                       )
    dob = DateField(null=True, verbose_name="出生日期")

    country = CharField(default="", max_length=128, verbose_name="国家")
    province = CharField(default="", max_length=128, verbose_name="省份")
    city = CharField(default="", max_length=64, verbose_name="城市")

    intro = CharField(max_length=500, default="", verbose_name="简介")

    job = CharField(default="", max_length=120, verbose_name="职业")

    avatar_key = CharField(default="", max_length=128, verbose_name="保存用户头像ID")

    lat = FloatField(default=0)
    lng = FloatField(default=0)
    geohash = CharField(default="", max_length=12)

    last_device_id = IntegerField(default=0, verbose_name="最后活动设备ID")
    reg_device_id = IntegerField(default=0, verbose_name="注册活动设备ID")
    reg_device_type = CharField(default="", verbose_name="注册设备类型")

    is_moderator = BooleanField(default=False,
                                index=True,
                                verbose_name="内容管理员",
                                help_text="可以客户端删除spam内容")

    state = IntegerField(default=1, verbose_name="状态")

    inviter_id = IntegerField(default=0, verbose_name="邀请人ID")
    last_login = DateTimeField(default=datetime.now)

    push_enabled = BooleanField(default=True, verbose_name="设置")

    realname = CharField(default="", max_length=128, verbose_name="真实姓名")
    identity_number = CharField(default="",
                                max_length=18,
                                verbose_name='身份证号码'
                                )

    credit = DecimalField(default=Decimal("0"),
                          max_digits=10,
                          decimal_places=2,
                          verbose_name="总账号余额")

    recharge_total = DecimalField(default=Decimal("0"),
                                  max_digits=10,
                                  decimal_places=2,
                                  help_text="总充值数")

    bean = IntegerField(default=0, verbose_name="云豆")
    points = IntegerField(default=0, verbose_name="积分")

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    pay_openid = CharField(help_text='微信支付是网页授权的 OpenID', null=True)

    def __str__(self):
        return self.name or str(self.id)

    @property
    def gender_name(self):
        return self.GENDERS.get(self.UserGender(self.gender).value, "未知")

    @property
    def screen_name(self):
        return self.name or self.mobile

    @property
    def state_name(self):
        return self.STATE_NAMES.get(self.state, "未知")

    @staticmethod
    def create_password(raw):
        """ 加密用户登录密码 """

        salt = create_token(8)
        passwd = '%s%s%s' % (salt, raw, 'yiyun')
        hsh = hashlib.sha1(passwd.encode("utf-8")).hexdigest()
        return "%s$%s" % (salt, hsh)

    @staticmethod
    def check_password(passwd, raw):
        """ 验证用户登录密码"""

        if not passwd or '$' not in passwd:
            return False
        salt, hsh = passwd.split('$', 1)
        new_passwd = '%s%s%s' % (salt, raw, 'yiyun')
        verify = hashlib.sha1(new_passwd.encode("utf-8")).hexdigest()
        return verify == hsh

    def generate_auth_token(self, device_id=None, expiration=3600):
        """ 生成用户 AccessToken

            Args:
                device_id: 设备ID
                expiration: 过期时间,单位:秒
        """

        playload = {
            'id': self.id,
            'exp': int(time.time()) + expiration
        }

        if device_id:
            playload['device'] = device_id

        access_token = jwt.encode(playload,
                                  key=app.settings['secret_key'],
                                  algorithm='HS256')

        return b"2.0@%s" % access_token

    @staticmethod
    def verify_auth_token(token, device_id=None):
        """ 验证AccessToken

            Args:
                token:
                device_id: 如果指定设备ID,设备ID与AccessToken不相符则验证失败
        """

        token = token.lstrip("2.0@")
        data = jwt.decode(token, key=app.settings[
                          'secret_key'], algorithm='HS256')

        # 指定设备ID与AccessToken中的设备ID不相符则验证失败
        if device_id is not None and data.get("device", "") != device_id:
            return None, None

        user = User.get_or_none(id=data['id'])
        return user, data

    def is_authenticated(self):
        if self.id > 0:
            return True

        return False

    def is_anonymous(self):
        if self.id > 0:
            return False

        return True

    def is_active(self):
        return self.state == 1

    def get_id(self):
        return self.id

    @cached_property
    def age(self):
        if not self.dob:
            return "未知"

        return (date.today() - self.dob).days / 365

    @cached_property
    def public_info(self):
        self._public_info = self.to_dict(
            exclude=[User.password, User.avatar_key, User.geohash,
                     User.last_device_id, User.reg_device_id, User.updated,
                     User.push_enabled, User.reg_device_type]
        )

        self._public_info['avatar'] = User.get_cover_urls(self.avatar_key)

        return self._public_info

    @cached_property
    def list_info(self):
        self._list_info = self.to_dict(
            only=[User.id, User.name, User.gender, User.lat, User.lng,
                  User.signature, User.city, User.roles]
        )

        self._list_info['avatar'] = User.get_cover_urls(self.avatar_key)

        return self._list_info

    @cached_property
    def info(self):
        info = self.to_dict(
            exclude=[User.password, User.avatar_key, User.geohash,
                     User.last_device_id, User.reg_device_id, User.updated,
                     User.reg_device_id, User.reg_device_type]
        )

        info['avatar'] = User.get_cover_urls(self.avatar_key)

        return info

    @cached_property
    def mini_info(self):
        self._mini_info = self.to_dict(
            only=[User.id, User.name, User.gender, User.roles,
                  User.dob, User.lat, User.lng]
        )

        self._mini_info['avatar'] = User.get_cover_urls(self.avatar_key)

        return self._mini_info

    def get_info(self):
        return self.info

    @property
    def avatar(self):
        cover_url = app.settings['avatar_url'].rstrip('/')
        return User.get_cover_urls(self.avatar_key, cover_url=cover_url)

    @property
    def avatar_url(self):
        if not self.avatar:
            return ""
        return "%s%s" % (self.avatar['url'], self.avatar['sizes'][0])

    def get_avatar_url(self, size='256'):
        if not self.avatar_key:
            return ""

        cover_url = app.settings['avatar_url'].rstrip('/')
        cover_key = self.avatar_key.split(":")[-1]

        return "%s/%s!c%s" % (cover_url, cover_key, size)


class UserLoginLog(BaseModel):

    """ 用户登录记录 """

    device_type = CharField(default="", max_length=16, index=True)
    device_id = IntegerField(default=0, index=True)

    user_id = IntegerField(index=True)
    ip = CharField(default="", max_length=15)
    created = DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'user_login_log'


class UserAuthData(BaseModel):

    """第三方认证绑定
    """

    class Meta:
        db_table = 'user_auth_data'

        indexes = (
            (('service', 'user_id', ), True),
        )

    class UserAuthService(Enum):
        qq = "qq"
        weixin = "weixin"
        weibo = "weibo"

    SERVICES = {
        UserAuthService.qq: "QQ",
        UserAuthService.weixin: "微信",
        UserAuthService.weibo: "微博",
    }

    service = CharField(max_length=12)
    user_id = IntegerField()

    openid = CharField(max_length=250)
    nickname = CharField(default="")

    access_token = CharField()
    expires_in = DateTimeField(null=True)

    userinfo = JSONTextField(null=True)

    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)

    @classmethod
    def get_service_name(cls, service):
        return cls.SERVICES.get(cls.UserAuthService(service), "未知")

    @cached_property
    def info(self):
        self._info = self.to_dict(
            only=[UserAuthData.nickname, UserAuthData.expires_in,
                  UserAuthData.access_token, UserAuthData.openid]
        )

        return self._info
