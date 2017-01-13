import time

import tornado.escape
import tornado.web
from urllib.parse import urljoin
from datetime import datetime, timedelta

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile
from yiyun.models import Team, TeamWeixin
from .forms.settings import TeamWeixinForm

from yiyun.ext.wx_comp import WxCompMixin
from yiyun import tasks


class WxMPBaseHandler(ClubBaseHandler, WxCompMixin):

    pass


@club_app.route(r"/wxmp/bind", name="club_wxmp_bind")
class Bind(WxMPBaseHandler):

    def get(self):
        if self.get_argument("auth_code", None):
            auth_info = self.get_query_auth(self.get_argument("auth_code"))

            team_weixin = TeamWeixin.get_or_none(
                appid=auth_info['authorizer_appid'])

            if team_weixin and team_weixin.team_id != self.current_team.id:
                self.flash("绑定失败：此微信公众号已绑定到其他俱乐部", category='danger')
                self.redirect(self.reverse_url("club_settings_weixin"))
                return

            if self.current_team.wx_appid and \
                    auth_info['authorizer_appid'] != self.current_team.wx_appid:

                self.flash("重新授权失败：新授权公众号与已绑定公众号不符", category='danger')
                self.redirect(self.reverse_url("club_settings_weixin_info"))
                return

            wx_info = self.get_authorizer_info(auth_info['authorizer_appid'])

            TeamWeixin.insert(
                team_id=self.current_team.id,

                access_token=auth_info['authorizer_access_token'],
                refresh_token=auth_info['authorizer_refresh_token'],
                expires_in=time.time() + auth_info['expires_in'] - 600,

                head_img=wx_info['authorizer_info'].get("head_img", ""),
                qrcode_url=wx_info['authorizer_info']["qrcode_url"],
                appid=wx_info['authorization_info']["authorizer_appid"],

                service_type=wx_info['authorizer_info'][
                    "service_type_info"]["id"],
                verify_type=wx_info['authorizer_info'][
                    "verify_type_info"]["id"],

                alias=wx_info['authorizer_info']["alias"],
                user_name=wx_info['authorizer_info'].get("user_name", ""),
                nick_name=wx_info['authorizer_info'].get("nick_name", ""),

                open_store=wx_info['authorizer_info'][
                    "business_info"]['open_store'],
                open_scan=wx_info['authorizer_info'][
                    "business_info"]['open_scan'],
                open_pay=wx_info['authorizer_info'][
                    "business_info"]['open_pay'],
                open_card=wx_info['authorizer_info'][
                    "business_info"]['open_card'],
                open_shake=wx_info['authorizer_info'][
                    "business_info"]['open_shake'],
                permissions=[str(i['funcscope_category']['id'])
                             for i in wx_info['authorization_info']['func_info']]
            ).upsert().execute()

            Team.update(
                wx_appid=auth_info['authorizer_appid'],
            ).where(
                Team.id == self.current_team.id
            ).execute()

            self.flash("绑定微信公众号成功！", category='success')
            self.redirect(self.reverse_url("club_settings_weixin"))
            return

        redirect_uri = urljoin(self.request.full_url(),
                               self.reverse_url("club_wxmp_bind")
                               )

        self.authorize_redirect(redirect_uri)


@club_app.route(r"/wxmp/bind/callback", name="club_wxmp_bind_callback")
class BindCallback(WxMPBaseHandler):
    """授权事件接收"""

    login_required = False
    team_required = False

    def post(self):
        signature = self.get_argument("signature", None)
        msg_signature = self.get_argument("msg_signature", None)
        timestamp = self.get_argument("timestamp", None)
        nonce = self.get_argument("nonce", None)

        if not self.check_signature(signature, timestamp, nonce):
            raise tornado.web.HTTPError(403)

        self.parse_message(self.request.body.decode(),
                           msg_signature=msg_signature,
                           timestamp=timestamp,
                           nonce=nonce)

        message = self.get_message()
        if message.type == "component_verify_ticket":
            self.set_component_verify_ticket(message.ticket, expires=1200)

        self.write("success")


@club_app.route(r"/wxmp/([^/]+)/receive_message",
                name="club_wxmp_receive_message")
class ReceiveMessage(WxMPBaseHandler):
    """docstring for ReceiveMessage"""

    login_required = False
    team_required = False

    def post(self, app_id):
        signature = self.get_argument("signature", None)
        msg_signature = self.get_argument("msg_signature", None)
        timestamp = self.get_argument("timestamp", None)
        nonce = self.get_argument("nonce", None)

        if not self.check_signature(signature, timestamp, nonce):
            raise tornado.web.HTTPError(403)

        self.logger.debug("receive_message: %s \n query: %s" % (self.request.body,
                                                                self.request.query))

        self.parse_message(self.request.body.decode(),
                           msg_signature=msg_signature,
                           timestamp=timestamp,
                           nonce=nonce)

        message = self.get_message()

        if app_id == 'wx570bc396a51b8ff8':
            self.answer_test(message)
            return

        self.logger.debug("msg_type: %s form %s" % (message.type, app_id))

        team = Team.get_or_none(wx_appid=app_id)
        if team is None:
            self.write("success")
            return

        if message.type == "subscribe":
            self.reply_subscribe(team, message)

        elif message.type == "text":
            self.reply_text(team, message)

        else:
            self.write("success")

    def reply_subscribe(self, team, message):

        weixin = TeamWeixin.get_or_none(team_id=team.id)
        if weixin is None or not weixin.reply_subscribe:
            self.write("success")
            return

        msg = weixin.reply_subscribe
        if weixin.reply_include_url:
            msg += "\n\n" + team.get_mini_url()

        reply = self.wechat.response_text(msg)
        self.set_header("Content-Type", "text/xml")
        self.write(reply)

    def reply_text(self, team, message):
        if message.content.strip() == "test":
            reply = self.wechat.response_text("good")
            self.set_header("Content-Type", "text/xml")
        else:
            reply = "success"

        self.write(reply)

    def answer_test(self, message):
        """ 响应公众号第三方平台测试消息
        """

        reply = "success"
        if hasattr(message, "event"):
            reply = self.wechat.response_text(
                "%sfrom_callback" % message.event)
            self.set_header("Content-Type", "text/xml")

        elif message.type == 'text' and message.content == "TESTCOMPONENT_MSG_TYPE_TEXT":
            self.set_header("Content-Type", "text/xml")
            reply = self.wechat.response_text(
                "TESTCOMPONENT_MSG_TYPE_TEXT_callback")

        elif message.type == 'text' and message.content.startswith("QUERY_AUTH_CODE:"):
            auth_code = message.content.split(':')[1]
            tasks.wxmp.reply_tester.delay(auth_code, message.source)

        self.write(reply)


@club_app.route(r"/settings/weixin/bind", name="club_settings_weixin_bind")
class WeixinBindSettings(ClubBaseHandler):
    """docstring for WeixinBindSettings"""

    def get(self):
        self.render("settings/weixin_bind.html")


@club_app.route(r"/settings/weixin", name="club_settings_weixin")
class WeixinSettings(ClubBaseHandler):
    """docstring for WeixinSettings"""

    def get(self):

        weixin = TeamWeixin.get_or_none(team_id=self.current_team.id)
        form = TeamWeixinForm(obj=weixin)

        self.render("settings/weixin_basic.html", form=form)

    def post(self):
        form = TeamWeixinForm(self.arguments)
        if form.validate():
            weixin = TeamWeixin.get_or_none(team_id=self.current_team.id)
            if weixin is None:
                weixin = TeamWeixin(team_id=self.current_team.id)

            form.populate_obj(weixin)
            weixin.save()

            self.flash("修改微信公众号设置成功！", category='success')
            self.redirect(self.reverse_url("club_settings_weixin"))
            return

        self.render("settings/weixin_basic.html", form=form)


@club_app.route(r"/settings/weixin/menu", name="club_settings_weixin_menu")
class WeixinSettingsMenu(ClubBaseHandler):
    """ 微信公众号菜单管理
    """

    def get(self):
        weixin = TeamWeixin.get_or_none(team_id=self.current_team.id)

        self.render("settings/weixin_menu.html", weixin=weixin)

    def post(self):

        action = self.get_argument("action")
        weixin = TeamWeixin.get_or_none(team_id=self.current_team.id)

        if action == "update":
            weixin.create_menu()

        elif action == "drop":
            weixin.delete_menu()

        self.write_success()


@club_app.route(r"/settings/weixin/info", name="club_settings_weixin_info")
class WeixinSettingsInfo(ClubBaseHandler):
    """ 已绑定微信公众号信息
    """

    def get(self):
        weixin = TeamWeixin.get_or_none(team_id=self.current_team.id)

        self.render("settings/weixin_info.html", weixin=weixin)
