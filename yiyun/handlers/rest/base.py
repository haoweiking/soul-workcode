from uuid import uuid4
import hashlib
import hmac
import base64

# from yiyun.handlers.api.base import *
from yiyun.models import Team
from yiyun.exceptions import ArgumentError
import json
import logging

import functools
import tornado.web
import jwt
from voluptuous import MultipleInvalid

from yiyun.ext.routing import route
from yiyun.handlers import BaseHandler
from yiyun.helpers import JSONEncoder, storage
from yiyun.libs.pagination import Page, Paginator
from yiyun.models import User, Client
from yiyun.exceptions import BaseError, ArgumentError
from yiyun import tasks

from yiyun.ext.parteam import ParteamRequestError, ParteamMixin

rest_app = route(prefix='/api/2')


class ApiException(BaseError):
    pass


class ApiBaseHandler(BaseHandler, ParteamMixin):

    verify_sign = True
    app_version = None
    device_id = 0
    device_type = ""
    secret_key = None

    per_page = 20
    paginator_class = None

    def get_current_user(self):
        access_token = self.get_access_token()
        logging.debug("get access token: {0}".format(access_token))
        if access_token:
            if access_token.startswith("2.0@"):
                try:
                    user, data = User.verify_auth_token(access_token)
                    if user is None:
                        self.logger.debug("非法会话: %s" % data)
                        raise ApiException(1004, "非法会话，用户不存在", status_code=401)

                    if not user.is_active():
                        raise ApiException(1005, "账号被禁止登录", status_code=401)

                    return user

                except jwt.ExpiredSignatureError:
                    raise ApiException(1002, "会话已过期，请重新登录", status_code=401)

                except jwt.InvalidTokenError:
                    raise ApiException(1003, "非法会话，请重新登录", status_code=403)
            else:
                user_info = self.get_session(access_token)
                user_info['id'] = user_info['userId']

                return storage(user_info)

        return None

    def get_access_token(self):
        auth_code = self.request.headers.get("X-Access-Token", None)
        if auth_code:
            return str(auth_code).strip()

        auth_code = self.get_secure_cookie("access-token")
        if auth_code:
            return str(auth_code.strip())

        return None

    def prepare(self):
        super(ApiBaseHandler, self).prepare()

        api_key = self.request.headers.get("X-Api-Key", None)
        signature = self.request.headers.get("X-Signature", None)
        timestamp = self.request.headers.get("X-Timestamp", "")
        nonce = self.request.headers.get("X-Nonce", "")
        content_type = self.request.headers.get("Content-Type", "")

        self.app_version = self.request.headers.get("X-App-Version", None)

        if self.verify_sign:
            if not api_key:
                raise ApiException(401, "没有ApiKey")

            client = Client.get_client(api_key)
            if not client:
                raise ApiException(401, "ApiKey有误")

            self.device_type = client['device_type'] or ""
            self.secret_key = client['secret']

            if client['verify_sign']:
                arguments = []
                for k in self.request.arguments:
                    arguments.append("%s=%s" % (k, self.get_argument(k)))

                arguments = sorted(arguments)

                json_body = ""
                if content_type.endswith("json"):
                    json_body = base64.b64encode(
                        self.request.body.decode().strip().encode()).decode()

                string_to_sign = "%s%s%s%s%s%s" % (
                    self.request.method.upper(),
                    self.request.path, "&".join(arguments), json_body,
                    timestamp, nonce)

                string_signature = self.generate_signature(client['secret'],
                                                           string_to_sign)

                if not signature or signature != string_signature.decode():
                    raise ApiException(401, "签名不正确")

    def generate_signature(self, secret, message):
        hmac_hash = hmac.new(secret.encode(), message.encode(),
                             digestmod=hashlib.sha256
                             ).digest()

        return base64.b64encode(hmac_hash)

    def write_error(self, status_code, **kwargs):

        error_code = status_code
        error = self._reason or ""
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            log_message = None
            if isinstance(exception, ApiException):
                status_code = exception.status_code
                error_code = exception.error_code
                status_code = exception.status_code
                error = exception.message
                log_message = exception.log_message

            elif isinstance(exception, BaseError):
                status_code = exception.status_code
                error_code = exception.error_code
                status_code = exception.status_code
                error = exception.message
                log_message = exception.log_message

            elif isinstance(exception, tornado.web.HTTPError):
                log_message = exception.log_message

                if exception.reason:
                    error = exception.reason

                elif exception.log_message:
                    error = exception.log_message

            elif isinstance(exception, Exception):
                error = "%s: %s" % (
                    exception.__class__.__name__, str(exception))

                log_message = error

            if log_message:
                self.logger.error("Error: %s" % log_message)

            if self.application.sentry_client:
                self.captureException()

        elif 'error' in kwargs:
            error = kwargs['error']

        if 'error_code' in kwargs:
            error_code = kwargs['error_code']

        self.set_status(status_code)
        self.set_header('Content-Type', 'application/json')
        self.finish({
            "error_code": error_code,
            "error": error
        })

    def write_success(self, **kwargs):
        kwargs['status'] = "ok"
        self.write(kwargs)

    def write(self, chunk):
        if isinstance(chunk, dict):
            if self.settings['debug']:
                chunk = json.dumps(chunk,
                                   ensure_ascii=False,
                                   sort_keys=True,
                                   cls=JSONEncoder
                                   ).replace("</", "<\\/")
            else:
                chunk = json.dumps(
                    chunk, cls=JSONEncoder).replace("</", "<\\/")

            self.set_header("Content-Type", "application/json; charset=UTF-8")

        self.add_header('Access-Control-Allow-Origin', '*')
        self.add_header('Access-Control-Allow-Methods', '*')

        super(ApiBaseHandler, self).write(chunk)

    def finish(self, chunk=None):
        self.set_header("X-Request-Time", "%0.0fms" %
                        (self.request.request_time() * 1000))
        super(ApiBaseHandler, self).finish(chunk)

    def paginate_query(self, query):
        """
        对 Query 进行分页处理
        Args:
            query:

        Returns: Query

        """

        number = self.get_argument('page', 1)
        try:
            number = int(number)
        except TypeError:
            number = 1

        try:
            per_page = int(self.get_argument('limit', 20))
        except TypeError:
            per_page = self.per_page

        page = Paginator(query, per_page=per_page).page(number=number)
        return page

    def render_page_info(self, page):
        """
        输出分页信息
        Args:
            page: Page

        Returns: dict

        """
        return {
            'total': page.paginator.count or 0,
            'num_pages': page.paginator.num_pages or 0,
            'previous_page': page.previous_page_number() or 0,
            'current_page': page.number or 0,
            'next_page': page.next_page_number() or 0,
            'per_page': page.paginator.per_page or 0
        }

    def get_paginated_data(self, page: Page=None, **kwargs) -> dict:
        """
        获取分页后的数据
        Args:
            page: Page,

        Returns: dict()
            num_pages: int, 总页数,
            previous_page: int, 上一页
            current_page: int, 当前页码
            next_pate: int, 下一页
            total: 总数
            per_page: 每页返回数
            results: list, 查询结果

        """
        data = self.render_page_info(page)

        if page:
            data['results'] = [item.info for item in page]

        data.update(kwargs)

        return data

    # @property
    # def validated_arguments(self):
    #     """
    #     获取已校验的请求参数
    #     Returns:
    #
    #     """
    #     assert hasattr(self, '_validated_arguments'), \
    #         'request.arguments 未校验, 先使用校验装饰器'
    #
    #     # 如果校验后表单为空, 提示异常
    #     if not self._validated_arguments:
    #         raise ApiException(400, "表单错误, 请填写属性和值")
    #     return self._validated_arguments


class BaseClubAPIHandler(ApiBaseHandler):
    """
    俱乐部 API 父类,
    """
    # TODO: 实现 OAuth 或 Authorization-backend

    login_required = True
    filter_classes = None

    @property
    def session_id(self):

        session_id = self.get_secure_cookie("session_id")
        if not session_id:
            session_id = uuid4().hex
            self.set_secure_cookie(
                "session_id", session_id, expires_days=None)

        return session_id

    def prepare(self):
        super(BaseClubAPIHandler, self).prepare()

    def get_paginated_data(self, page: Page, alias='results', serializer=None,
                           serializer_kwargs=None, **kwargs) -> dict:
        """
        获取分页后的数据
        Args:
            page: Page,
            alias:
            serializer
            serializer_kwargs:

        Returns: dict()
            num_pages: int, 总页数,
            previous_page: int, 上一页
            current_page: int, 当前页码
            next_pate: int, 下一页
            total: 总数
            per_page: 每页返回数
            results: list, 查询结果

        """
        data = self.render_page_info(page)

        if page:
            if serializer:
                if not isinstance(serializer_kwargs, dict):
                    serializer_kwargs = {}

                data[alias] = [serializer(row, **serializer_kwargs).data for
                               row in page]
            else:
                data[alias] = [row.info for row in page]

        else:
            data[alias] = []

        data.update(kwargs)

        return data

    def filter_query(self, query):
        filter_classes = self.filter_classes
        if not filter_classes:
            return query

        assert isinstance(filter_classes, (tuple, list)), \
            'The attribute `filter_classes` must be tuple or list'

        for filter_class in filter_classes:
            query = filter_class(query, self.request.query_arguments).q
        return query

    def upload_file(self, field, to_bucket, to_key,
                    allow_exts=('jpg', 'jpeg', 'png', 'gif', 'webp'),
                    required=True):

        upload_file = self.request.files.get(field)
        if not upload_file:
            if not required:
                return
            raise ArgumentError(400, "没有上传")

        filename = upload_file[0]['filename']
        if not filename or filename.split(".")[-1].lower() not in allow_exts:
            raise ArgumentError(400, "上传格式不支持")

        ext = filename.split(".")[-1].lower()
        file_body = upload_file[0]['body']
        if not file_body:
            raise ArgumentError(400, "上传文件为空")

        # 最大5M
        elif len(file_body) > 5100000:
            raise ArgumentError(400, "上传文件不能超过5M")

        to_key = to_key + "." + ext
        ret, info = tasks.qiniu_tool.put_data(to_bucket, to_key,
                                              file_body,
                                              check_crc=True
                                              )
        if not ret:
            self.logger.debug("上传文件到七牛失败：%s" % info)
            raise ArgumentError(500, "保存失败，请稍后重试")

        return "%s:%s" % (to_bucket, to_key)


def authenticated(method):
    """Decorate methods with this to require that the user be logged in.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):

        if not self.current_user:
            raise ApiException(403, "Access denied")

        return method(self, *args, **kwargs)

    return wrapper


def validate_arguments_with(schema):
    """
    装饰器, 校验请求参数是否正确
    Args:
        method:
        schema: voluptuous.Schema
    """

    def func_wrapper(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            content_type = self.request.headers.get("Content-Type")

            if content_type and content_type.startswith("application/json"):
                _arguments = json.loads(self.request.body.decode())
            else:
                _arguments = {}
                for key in self.request.arguments.keys():
                    _arguments[key] = self.get_argument(key)

            try:
                self._validated_arguments = schema(_arguments) or {}

            except MultipleInvalid as e:
                errors = []
                for error in e.errors:
                    errors.append({
                        "field": str(error.path[-1]),
                        "message": str(error.msg)
                    })

                logging.debug(errors)
                raise ApiException(422, errors)
            return method(self, *args, **kwargs)
        return wrapper
    return func_wrapper
