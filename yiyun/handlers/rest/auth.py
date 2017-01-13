import logging
import random
import io
from datetime import datetime, timedelta

import tornado.web
import tornado.gen
from voluptuous import Schema, REMOVE_EXTRA, Required, Coerce, All, Length, Any

from yiyun.helpers import is_mobile, intval, create_token
from .base import (rest_app, BaseClubAPIHandler, authenticated,
                   validate_arguments_with, ApiException)

from yiyun.libs.captcha import create_captcha
from yiyun.ext import auth
from yiyun.models import Device, User, UserAuthData
from yiyun import tasks
from .schemas.base import phone_validator, datetime_validator, email_validator


class BaseRestAPIHandler(BaseClubAPIHandler):
    pass


class AuthBaseHandler(BaseRestAPIHandler):

    def verify_mobile(self, mobile, verify_code):
        """验证手机验证码
        """

        if not verify_code or not mobile:
            self.logger.debug('verify_code: [{0}], mobile[{1}]'
                              .format(verify_code, mobile))
            return False

        if (self.settings['debug'] or mobile in ("18088998899", "18088998898"))\
                and verify_code == "8888":
            return True

        code = self.redis.get("yiyun:mobile:verify_code:%s" % mobile)
        return code == verify_code

    def save_verify_code(self, mobile, verify_code):

        self.redis.set("yiyun:mobile:verify_code:%s" % mobile, verify_code)

        # 30分钟内有效
        self.redis.expire("yiyun:mobile:verify_code:%s" % mobile, 1800)

    def create_session(self, user):

        session_expires = self.settings.get("session_expires", 3600 * 24 * 360)
        access_token = user.generate_auth_token(expiration=session_expires)

        self.set_secure_cookie("access-token", access_token)

        return {"session": {
                "access_token": access_token,
                "expires_in": session_expires
                }, "current_user": user.get_info()
                }

    def register_or_login(self, service, openid, access_token, expires_in,
                          nickname, gender, head_url, auth_data):

        try:
            user = User.select().join(
                UserAuthData,
                on=(UserAuthData.user_id == User.id)
            ).where(
                (UserAuthData.service == service
                 ) & (UserAuthData.openid == openid)
            ).get()

        except User.DoesNotExist:
            user = None

        if self.current_user:

            # 已绑定到其它账号
            if user and user.id != self.current_user.id:
                raise ApiException(403, "此%s账号已被其他用户使用" %
                                   UserAuthData.get_service_name(service))

            # 已绑定到自己账号
            elif user and user.id == self.current_user.id:
                UserAuthData.update(
                    access_token=access_token,
                    expires_in=expires_in,
                    userinfo=auth_data
                ).where(
                    (UserAuthData.service == service
                     ) & (UserAuthData.user_id == user.id)
                ).execute()

            # 已绑定其它账号
            elif UserAuthData.select().where(
                (UserAuthData.service == service
                 ) & (UserAuthData.user_id == self.current_user.id
                      ) & (UserAuthData.openid != openid)
            ).exists():

                raise ApiException(403, "你已绑定其他%s账号" %
                                   UserAuthData.get_service_name(service))

            # 已登录执行绑定
            else:
                UserAuthData.create(
                    service=service,
                    user_id=self.current_user.id,
                    openid=openid,
                    nickname=nickname,
                    access_token=access_token,
                    expires_in=expires_in,
                    userinfo=auth_data
                )

                if self.device_id > 0:
                    User.update(
                        last_device_id=self.device_id
                    ).where(
                        User.id == self.current_user.id
                    ).execute()

            self.write(self.create_session(self.current_user))

        else:
            # 已注册用户直接登录
            if user:
                update = {
                    "last_login": datetime.now()
                }

                if self.device_id > 0:
                    update["last_device_id"] = self.device_id

                User.update(
                    **update
                ).where(
                    User.id == user.id
                ).execute()

                UserAuthData.update(
                    access_token=access_token,
                    expires_in=expires_in,
                    userinfo=auth_data
                ).where(
                    (UserAuthData.service == service
                     ) & (UserAuthData.user_id == user.id)
                ).execute()

            # 未注册用户先注册
            else:

                with self.db.transaction() as txn:
                    if User.select().where(
                        User.name == nickname
                    ).exists():
                        if nickname == "qzuser":
                            name = "%s_%s" % (
                                nickname, random.randint(100000, 999999))
                        else:
                            name = "%s_%s" % (
                                nickname, random.randint(100, 999))

                    else:
                        name = nickname

                    user = User.create(
                        name=name,
                        gender=gender,
                        mobile_verifyed=False,
                        password=None,
                        reg_device_id=self.device_id,
                        last_device_id=self.device_id,
                        last_login=datetime.now(),
                        im_username=create_token(32).lower(),
                        im_password=create_token(16),
                    )

                    UserAuthData.create(
                        service=service,
                        user_id=user.id,
                        openid=openid,
                        nickname=nickname,
                        access_token=access_token,
                        expires_in=expires_in,
                        userinfo=auth_data
                    )

                    # 将手机好加到 redis, 匹配好友需要
                    if user.mobile:
                        self.redis.sadd('mobile:registered', user.mobile)

                    # 从第三方下载头像
                    if head_url:
                        tasks.user.update_avatar_by_url.delay(
                            user.id, head_url)

            if user and self.device_id:
                Device.update(
                    owner_id=user.id
                ).where(
                    Device.id == self.device_id
                ).execute()

            self.write(self.create_session(user))


@rest_app.route(r"/auth/captcha.jpg", name="rest_captcha_image")
class CaptchaImage(AuthBaseHandler):

    login_required = False
    team_required = False

    def get(self):

        image, chars = create_captcha()

        self.redis.set("user:auth:captcha:%s" %
                       self.session_id, "".join(chars).lower(), ex=300)

        o = io.BytesIO()
        image.save(o, format="JPEG")

        s = o.getvalue()

        self.set_header('Expires', '0')
        self.set_header(
            'Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))
        self.write(s)


@rest_app.route("/auth/register_device")
class RegisterDevice(AuthBaseHandler):

    """移动设备登记
    """

    @validate_arguments_with(Schema({
        Required("install_id"): str,
        Required("push_id"): All(str, Length(max=128)),
        Required("device_token"): str,
        Required("device_type"): str,
        Required("app_version"): str
    }, extra=REMOVE_EXTRA))
    def post(self):

        form = self.validated_arguments

        if not device:
            device = Device.create(
                install_id=form['install_id'],
                push_id=form['push_id'],
                device_token=form['device_token'],
                device_type=form['device_type'],
                app_version=form['app_version'],
            )

        else:
            Device.update(
                device_token=form['device_token'],
                app_version=form['app_version']
            ).where(
                Device.id == device.id
            ).execute()

        self.write({
            "device_id": device.id
        })


@rest_app.route("/auth/request_verify_code")
class RequestVerifyCode(AuthBaseHandler):

    """请求发送短信验证码
        根据 action 发送不同目的的验证码
    """

    @validate_arguments_with(Schema({
        Required("mobile"): All(str, Length(max=11, min=11), phone_validator),
        Required("action"): Any("register", "login", "register_or_login",
                                "update_mobile", "forgot"),
        "password": str
    }, extra=REMOVE_EXTRA))
    def post(self):

        mobile = self.validated_arguments['mobile']
        action = self.validated_arguments['action']

        sent_times_key = "yiyun:mobile:%s:code_sent_times" % mobile
        if intval(self.redis.get(sent_times_key)) >= 5:
            raise ApiException(400, "你已重发5次，请稍后再试")

        # 有效期内发送相同的验证码
        verify_code = random.randint(1000, 9999)
        logging.debug('verify code for mobile[{0}]: {1}'
                      .format(mobile, verify_code))
        is_registered = User.select().where(User.mobile == mobile).exists()

        if action == "register" and is_registered:
            raise ApiException(1020, "手机号码已注册", status_code=400)

        if action in ('register_or_login', 'register', 'login'):
            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            if not self.settings["debug"]:
                tasks.message.send_sms_verifycode(mobile, verify_code)

            self.write_success(is_registered=is_registered)

        elif action == "forgot":

            if not is_registered:
                raise ApiException(400, "手机号码没有注册")

            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            tasks.message.send_sms_verifycode(mobile, verify_code)

            self.write_success()

        elif action == "update_mobile":

            if not self.current_user:
                raise ApiException(403, "登录后才能修改手机号")

            if is_registered:
                raise ApiException(403, "该号码已经使用，请更换")

            if self.current_user.password and \
                    not User.check_password(self.current_user.password,
                                            self.validated_arguments["password"]):
                raise ApiException(403, "密码不正确，不能修改手机号")

            # 保存验证码
            self.save_verify_code(mobile, verify_code)

            # 发短信
            tasks.message.send_sms_verifycode(mobile, verify_code)

            # 关联验证码与当前用户
            self.redis.set("yiyun:update_mobile:%s:verify_code:%s" % (
                mobile, verify_code), self.current_user.id)

            # 30分钟内有效
            self.redis.expire(
                "yiyun:update_mobile:%s:verify_code:%s" % (mobile, verify_code), 1800)

            self.write_success()

        # 30分钟内最多发送5次验证码
        sent_times = intval(self.redis.incr(sent_times_key))
        if sent_times == 1:
            self.redis.expire(sent_times_key, 1800)


@rest_app.route("/auth/login_verify_code")
class LoginVerifyCode(AuthBaseHandler):

    """使用手机号码和短信验证码登录
        如果没有注册会自动注册为新用户
    """

    @validate_arguments_with(Schema({
        Required("mobile", msg="手机号码不能为空"): All(str,
                                                Length(max=11, min=11),
                                                phone_validator),
        Required("verify_code", msg="短信验证不能为空"): str
    }, extra=REMOVE_EXTRA))
    @tornado.gen.coroutine
    def post(self):

        mobile = self.validated_arguments['mobile']
        verify_code = self.validated_arguments['verify_code']

        if not self.verify_mobile(mobile, verify_code):
            raise ApiException(400, "验证码错误，请重新输入")

        user = User.get_or_none(mobile=mobile)

        if not user:
            with self.db.transaction() as txn:
                user = User.create(
                    mobile=mobile,
                    mobile_verifyed=True,
                    reg_device_id=self.device_id,
                    last_device_id=self.device_id,
                    last_login=datetime.now(),
                )

        else:
            update = {
                "last_login": datetime.now()
            }

            if self.device_id > 0:
                update["last_device_id"] = self.device_id

            User.update(
                **update
            ).where(
                User.id == user.id
            ).execute()

        if user and self.device_id:
            User.update_device(user.id, self.device_id)

        self.write(self.create_session(user))


@rest_app.route("/auth/login")
class LoginByUsername(AuthBaseHandler):

    """ 使用手机号或邮箱和密码登录
    """

    @validate_arguments_with(Schema({
        Required("username", msg="用户名不能为空"): str,
        Required("password", msg="密码不能为空"): str
    }, extra=REMOVE_EXTRA))
    def post(self):

        username = self.validated_arguments['username'].lower()
        password = self.validated_arguments['password']

        if len(username) == 0 or len(password) == 0:
            raise ApiException(400, "用户名和密码不能为空")

        fail_times_key = "yiyun:user:%s:login_fail_times" % username
        if intval(self.redis.get(fail_times_key)) >= 5:
            raise ApiException(403, "密码错误次数太多，请休息10分钟再试")

        if is_mobile(username):
            user = User.get_or_none(mobile=username)

        elif username.find('@') > 0:
            user = User.get_or_none(email=username)

        else:
            raise ApiException(400, "用户名格式不正确，请填写手机号或电子邮箱")

        if not password or not user \
                or not User.check_password(user.password, password):

            fail_times = intval(self.redis.incr(fail_times_key))
            if fail_times == 1:
                self.redis.expire(fail_times_key, 600)

            raise ApiException(403, "密码有误，如果没有设置密码请使用手机号找回密码")

        # 重试次数归零
        self.redis.delete(fail_times_key)

        if not user.is_active():
            raise ApiException(403, "你的账户不可用，无法登录")

        update = {
            "last_login": datetime.now()
        }

        if self.device_id > 0:
            update["last_device_id"] = self.device_id

        User.update(
            **update
        ).where(
            User.id == user.id
        ).execute()

        if user and self.device_id:
            Device.update(
                owner_id=user.id
            ).where(
                Device.id == self.device_id
            ).execute()

        self.write(self.create_session(user))


class ThirdpartyAuthBaseHandler(AuthBaseHandler):

    @authenticated
    def delete(self, service):
        """ 取消绑定
        """

        try:
            auth = UserAuthData.select().where(
                (UserAuthData.service == service
                 ) & (UserAuthData.user_id == self.current_user.id)
            ).get()

        except UserAuthData.DoesNotExist:
            raise ApiException(400, "你还没有绑定%s账号" %
                               UserAuthData.get_service_name(service))

        if not self.current_user.mobile \
                and not self.current_user.email \
                and not UserAuthData.select().where(
                    (UserAuthData.service != service
                     ) & (UserAuthData.user_id == self.current_user.id)
                ).exists():

            raise ApiException(400, "此%s账号是你唯一的登录方式，不能解绑" %
                               UserAuthData.get_service_name(service))

        auth.delete_instance()

        self.set_status(204)


@rest_app.route(r"/auth/(weixin)")
class WeixinAuth(ThirdpartyAuthBaseHandler, auth.WeixinMixin):

    """ 使用微信登录
    """

    @validate_arguments_with(Schema({
        Required("code"): str,
        Required("platform"): Any("ios", "android", "web")
    }, extra=REMOVE_EXTRA))
    @tornado.gen.coroutine
    def post(self, service):

        code = self.validated_arguments['code']
        platform = self.validated_arguments['platform']

        if platform == "web":
            params = {
                'client_id': self.settings['weixin_web_appid'],
                'client_secret': self.settings['weixin_web_appsecret'],
                'code': code
            }

        else:
            params = {
                'client_id': self.settings['weixin_appid'],
                'client_secret': self.settings['weixin_appsecret'],
                'code': code
            }

        user = yield self.get_authenticated_user(**params)

        if not user or 'unionid' not in user:
            raise ApiException(400, "微信认证失败，请重试")

        gender = 'n'
        if user.get("sex", 0) == 1:
            gender = "m"
        elif user.get("sex", 0) == 2:
            gender = "f"

        expires_in = datetime.utcnow() + \
            timedelta(seconds=user.get("expires_in", 3600))

        auth_data = {
            "unionid": user['unionid'],
            "wx_openid": user['openid'],
            "wx_expires_in": expires_in.strftime("%Y-%m-%d %H:%M:%S") if expires_in else None,
            "wx_access_token": user['access_token'],
            "nickname": user['nickname']
        }

        self.register_or_login("weixin",
                               openid=user['unionid'],
                               access_token=user['access_token'],
                               expires_in=expires_in,
                               nickname=user['nickname'],
                               gender=gender,
                               head_url=user.get("headimgurl", None),
                               auth_data=auth_data
                               )


@rest_app.route(r"/auth/(weibo)")
class WeiboAuth(AuthBaseHandler, auth.WeiboMixin):

    """ 使用微博登录
    """

    @validate_arguments_with(Schema({
        Required("access_token"): str,
        Required("expires_in"): datetime_validator(),
        Required("uid"): Coerce(int)
    }, extra=REMOVE_EXTRA))
    @tornado.gen.coroutine
    def post(self, service):

        access_token = self.validated_arguments['access_token']
        expires_in = self.validated_arguments['expires_in']
        uid = self.validated_arguments['uid']

        response = yield self.weibo_request("/users/show.json",
                                            access_token=access_token,
                                            uid=uid)

        if not response or response.get("id", None) != intval(uid):
            raise ApiException(403, "新浪微博认证失败，请重试")

        # 头像
        if response.get("avatar_hd", None):
            head_url = response['avatar_hd']
        elif response.get("avatar_large", None):
            head_url = response['avatar_large']
        else:
            head_url = response.get("profile_image_url", None)

        gender = 'n'
        if response.get("gender", None) in ('m', 'f', ):
            gender = response['gender']

        auth_data = {
            "uid": uid,
            "domain": response.get("domain", ""),
            "screen_name": response.get("screen_name", ""),
            "access_token": access_token,
            "session_expires": expires_in
        }

        self.register_or_login("weibo",
                               openid=uid,
                               access_token=access_token,
                               expires_in=expires_in,
                               nickname=response.get("screen_name", ""),
                               gender=gender,
                               head_url=head_url,
                               auth_data=auth_data
                               )


@rest_app.route(r"/auth/(qq)")
class QQAuth(AuthBaseHandler, auth.QQMixin):

    """ 使用QQ登录
    """

    @validate_arguments_with(Schema({
        Required("access_token"): str,
        Required("expires_in"): datetime_validator(),
        Required("openid"): str,
        Required("platform"): Any("ios", "android", "web")
    }, extra=REMOVE_EXTRA))
    @tornado.gen.coroutine
    def post(self, service):

        access_token = self.validated_arguments['access_token']
        expires_in = self.validated_arguments['expires_in']
        openid = self.validated_arguments['openid']
        platform = self.validated_arguments['platform']

        if platform == "web":
            client_id = self.settings.get("qq_web_apiid")
        elif platform == "android":
            client_id = self.settings.get("qq_android_apiid")
        else:
            client_id = self.settings['qq_apiid']

        response = yield self.qq_request("/user/get_user_info",
                                         access_token=access_token,
                                         openid=openid,
                                         client_id=client_id,
                                         format='json')

        if not response or intval(response.get('ret', 0)) != 0:
            raise ApiException(403, "QQ绑定失败，请重试")

        if response.get("figureurl_qq_2", None) \
                and response.get("figureurl_qq_2", "").find("942FEA70050EEAFBD4DCE2C1FC775E56") == -1:
            head_url = response.get("figureurl_qq_2", None)

        elif response.get("figureurl_qq_1", None) \
                and response.get("figureurl_qq_1", "").find("942FEA70050EEAFBD4DCE2C1FC775E56") == -1:
            head_url = response.get("figureurl_qq_1", None)

        else:
            head_url = None

        gender = 'n'
        if response.get("gender", False) == '男':
            gender = 'm'
        elif response.get("gender", False) == '女':
            gender = 'f'

        auth_data = {
            "openid": openid,
            "nickname": response.get("nickname", ""),
            "access_token": access_token,
            "session_expires": expires_in
        }

        self.register_or_login("qq",
                               openid=openid,
                               access_token=access_token,
                               expires_in=expires_in,
                               nickname=response.get("nickname", ""),
                               gender=gender,
                               head_url=head_url,
                               auth_data=auth_data
                               )


@rest_app.route("/auth/refresh_token")
class RefreshToken(AuthBaseHandler):

    """在会话token过期前获取一个新的token"""

    @authenticated
    def get(self):
        self.write(self.create_session(self.current_user))


@rest_app.route("/auth/logout")
class Logout(AuthBaseHandler):

    """退出登录
        作废当前会话，同时取消设备绑定
    """

    def post(self):
        if self.device_id:
            Device.update(
                owner_id=0
            ).where(
                Device.id == self.device_id
            ).execute()

        self.clear_cookie("access-token")
        self.write_success()


@rest_app.route("/auth/forgot_password")
class ForgotPassword(AuthBaseHandler):

    """ 使用邮箱找回密码
        此接口会将验证码发送邮箱
    """

    @validate_arguments_with(Schema({
        Required("email", msg="用户名不能为空"): All(str, email_validator),
        Required("verify_code", msg="验证不能为空"): str,
        Required("new_password", msg="密码不能为空"): All(str, Length(min=6, max=32, msg="密码长度必须是6到32位"))
    }, extra=REMOVE_EXTRA))
    def post(self):

        email = self.validated_arguments['email']

        if email.find("@") <= 0:
            raise ApiException(400, "电子邮箱格式有误")

        user = User.get_or_none(email=email)

        if not user:
            raise ApiException(404, "你还没有注册或用户名有误")

        verify_code = self.redis.get("yiyun:email:verify_code:%s" % email)
        if not verify_code:
            verify_code = random.randint(1000, 9999)

        # 验证码两小时内有效
        self.redis.set("yiyun:email:verify_code:%s" % email, verify_code)
        self.redis.expire("yiyun:email:verify_code:%s" % email, 3600 * 24)

        # 发送验证邮件
        tasks.user.send_forgot_email.delay(
            user.name or email, email, verify_code)

        self.write_success()


@rest_app.route("/auth/reset_password")
class RestPassword(AuthBaseHandler):

    """使用手机号或邮箱和验证码重置密码
    """

    @validate_arguments_with(Schema({
        Required("username", msg="用户名不能为空"): str,
        Required("verify_code", msg="验证不能为空"): str,
        Required("new_password", msg="密码不能为空"): All(str, Length(min=6, max=32, msg="密码长度必须是6到32位"))
    }, extra=REMOVE_EXTRA))
    def post(self):

        username = self.validated_arguments['username']
        verify_code = self.validated_arguments['verify_code']
        new_password = self.validated_arguments['new_password']

        if is_mobile(username):
            if not self.verify_mobile(username, verify_code):
                raise ApiException(400, "验证码错误，请重新输入")

            user = User.get_or_none(mobile=username)
            if not user:
                raise ApiException(400, "手机号还没有注册")

            User.update(
                password=User.create_password(new_password)
            ).where(
                User.id == user.id
            ).execute()

        elif username.find("@") > 0:

            user = User.get_or_none(email=username)
            if not user:
                raise ApiException(400, "邮箱还没有注册")

            User.update(
                password=User.create_password(new_password)
            ).where(
                User.id == user.id
            ).execute()

        else:
            raise ApiException(400, "用户名格式有误，请填写手机号或电子邮箱")

        self.write_success()
