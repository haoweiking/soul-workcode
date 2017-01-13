# encoding: utf-8
import time
from datetime import datetime, timedelta
from decimal import Decimal

from .base import BaseModel

from peewee import (fn, BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured,
                    CompositeKey, IntegrityError)

from yiyun.ext.database import (GeoHashField, JSONTextField, ChoiceField,
                                ListField, PointField)

from cached_property import cached_property
from yiyun.core import current_app as app
from yiyun.models import User, Team
from yiyun.ext.wx_comp import WxCompMixin, WechatBasic


class TeamWeixin(BaseModel, WxCompMixin):
    """docstring for TeamWeixin"""

    class Meta:
        db_table = 'team_weixin'

    SERVICE_TYPES = {
        0: "订阅号",
        1: "订阅号（由历史老帐号升级后的订阅号）",
        2: "服务号"
    }

    VERIFY_TYPES = {
        -1: "未认证",
        0: "微信认证",
        1: "新浪微博认证",
        2: "腾讯微博认证",
        3: "已资质认证通过但还未通过名称认证",
        4: "已资质认证通过、还未通过名称认证，但通过了新浪微博认证",
        5: "已资质认证通过、还未通过名称认证，但通过了腾讯微博认证",
    }

    WEIXIN_PERMISSIONS = {
        1: "消息管理权限",
        2: "用户管理权限",
        3: "帐号服务权限",
        4: "网页服务权限",
        5: "微信小店权限",
        6: "微信多客服权限",
        7: "群发与通知权限",
        8: "微信卡券权限",
        9: "微信扫一扫权限",
        10: "微信连WIFI权限",
        11: "素材管理权限",
        12: "微信摇周边权限",
        13: "微信门店权限",
        14: "微信支付权限",
        15: "自定义菜单权限"
    }

    team_id = IntegerField(unique=True, primary_key=True)

    access_token = CharField(default="", max_length=128)
    refresh_token = CharField(default="", max_length=128)
    expires_in = IntegerField(default=0)

    reply_subscribe = TextField(default="", verbose_name="关注自动回复")
    reply_include_url = BooleanField(default=False, verbose_name="包含链接")

    head_img = CharField(verbose_name="授权方头像", max_length=128)
    qrcode_url = CharField(verbose_name="授权方头像", max_length=128)
    appid = CharField(verbose_name="授权方appid", max_length=32)

    service_type = IntegerField(
        verbose_name="授权方公众号类型", help_text="授权方公众号类型，0代表订阅号，1代表由历史老帐号升级后的订阅号，2代表服务号")
    verify_type = IntegerField(
        verbose_name="授权方认证类型", help_text="授权方认证类型，-1代表未认证，0代表微信认证，1代表新浪微博认证，2代表腾讯微博认证，3代表已资质认证通过但还未通过名称认证，4代表已资质认证通过、还未通过名称认证，但通过了新浪微博认证，5代表已资质认证通过、还未通过名称认证，但通过了腾讯微博认证")

    alias = CharField(default="", max_length=128,
                      help_text="授权方公众号所设置的微信号，可能为空")

    nick_name = CharField(max_length=128, help_text="授权方公众号的昵称")
    user_name = CharField(max_length=128, help_text="授权方公众号的原始ID")

    open_store = BooleanField(default=False, help_text="是否开通微信门店功能")
    open_scan = BooleanField(default=False, help_text="是否开通微信扫商品功能")
    open_pay = BooleanField(default=False, help_text="是否开通微信支付功能")
    open_card = BooleanField(default=False, help_text="是否开通微信卡券功能")
    open_shake = BooleanField(default=False, help_text="是否开通微信摇一摇功能")

    permissions = ListField()

    @property
    def redis(self):
        return app.redis

    @property
    def settings(args):
        return app.settings

    @cached_property
    def service_type_name(self):
        return self.SERVICE_TYPES.get(self.service_type, "未知")

    @cached_property
    def verify_type_name(self):
        return self.VERIFY_TYPES.get(self.verify_type, "未知")

    @cached_property
    def permission_names(self):
        return [self.WEIXIN_PERMISSIONS.get(int(i)) for i in self.permissions]

    @cached_property
    def wx_client(self):
        return WechatBasic(
            access_token=self.access_token,
            access_token_getfunc=self.get_access_token,
            appid=self.appid,
            appsecret=app.settings['wx_comp_appsecret'],  # 此appsecret并不会使用
        )

    def get_access_token(self):
        if self.expires_in < time.time():
            data = self.refresh_authorizer_token(
                self.appid, self.refresh_token)

            self.access_token = data['authorizer_access_token']
            self.refresh_token = data['authorizer_refresh_token']
            self.expires_in = int(time.time()) + data['expires_in'] - 60
            self.save()

        return self.access_token, self.expires_in

    def create_menu(self):
        self.wx_client.create_menu({'button': [{
            'type': 'view',
            'name': '近期活动',
            'url': "%s/c/%s" % (app.settings['club_url'], self.team_id)
        }, {
            'type': 'view',
            'name': '我的活动',
            'url': "%s/c/%s/my" % (app.settings['club_url'], self.team_id)
        }, {
            'type': 'view',
            'name': '俱乐部',
            'url': "%s/c/%d/desc" % (app.settings['club_url'], self.team_id)
        }]})

    def delete_menu(self):
        self.wx_client.delete_menu()

    def can_create_menu(self):
        """ 是否支持修改菜单

            只有认证后的订阅号和服务号可以自定义菜单
        """

        if "15" not in self.permissions:
            return False

        if self.service_type in (0, 1) and self.verify_type == -1:
            return False

        return True
