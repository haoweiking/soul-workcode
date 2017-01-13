from __future__ import division

import math
import json
from base64 import urlsafe_b64encode
from uuid import uuid4
import urllib.parse as urlparse
from urllib.parse import urlencode
import requests

import tornado.web
from tornado.httputil import url_concat
from tornado.escape import parse_qs_bytes, utf8
from tornado.auth import (escape, httpclient, urllib_parse)

from yiyun.ext.routing import route
from yiyun.ext.mixins import FlashMessageMixin
from yiyun.handlers import BaseHandler
from yiyun.libs.pagination import Pagination

from yiyun.exceptions import BaseError, ArgumentError
from yiyun.models import User, Team
from yiyun.helpers import intval, decimalval, merge_dict
from yiyun import tasks

club_app = route(prefix="/club")


class ClubBaseHandler(BaseHandler, FlashMessageMixin):

    login_required = True
    team_required = True
    email_verified_required = True

    PER_PAGE = 20

    def initialize(self, *args, **kwargs):
        super(ClubBaseHandler, self).initialize(*args, **kwargs)

    def prepare(self):
        super(ClubBaseHandler, self).prepare()

        if self.login_required:
            if not self.current_user:
                return self.redirect_login()

        if self.email_verified_required:
            if not self.current_user:
                return self.redirect_login()
            if not self.current_user.email_verified:
                url = self.reverse_url("club_wait_email_verify")
                return self.redirect(url)

        if self.team_required:
            if not self.current_user:
                return self.redirect_login()
            if not self.current_team:
                return self.redirect(self.reverse_url("club_create"))
            if self.current_team.state == 0:
                return self.redirect(self.reverse_url("club_wait_approve"))

    def redirect_login(self):
        url = self.get_login_url()
        if "?" not in url:
            if urlparse.urlsplit(url).scheme:
                next_url = self.request.full_url()
            else:
                next_url = self.request.uri
            url += "?" + urlencode(dict(next=next_url))
        self.redirect(url)

    def get_template_path(self):
        return self.application.settings.get("template_path") + "/club"

    def get_template_namespace(self):
        namespace = super(ClubBaseHandler, self).get_template_namespace()
        namespace["xhr_url_names"] = self.xhr_url_names
        namespace['urlsafe_b64encode'] = urlsafe_b64encode
        namespace['merge_dict'] = merge_dict
        return namespace

    def get_login_url(self):
        return self.reverse_url("club_auth_login")

    def get_current_user(self):
        user = self.get_secure_cookie("club_session")
        if not user:
            return None

        try:
            userinfo = json.loads(user.decode("utf-8"))

            if userinfo and userinfo.get("id", None):
                user = User.get_or_none(id=userinfo['id'])

                if user is not None:
                    return user
        except:
            return None

    def get_current_team(self):
        if not self.current_user:
            return None

        return Team.get_or_none(owner_id=self.current_user.id)

    @property
    def current_team(self):
        if not hasattr(self, "_current_team"):
            self._current_team = self.get_current_team()
        return self._current_team

    @property
    def session_id(self):
        session_id = self.get_secure_cookie("session_id")
        if not session_id:
            session_id = uuid4().hex
            self.set_secure_cookie(
                "session_id", session_id, expires_days=None)

        return session_id

    def render_string(self, template_name, **kwargs):
        kwargs['current_team'] = self.current_team
        kwargs['url_for_page'] = self.url_for_page
        kwargs['decimalval'] = decimalval
        return super(ClubBaseHandler, self).render_string(template_name, **kwargs)

    def verify_mobile(self, mobile, verify_code):
        """验证手机验证码
        """

        if not verify_code or not mobile:
            return False

        if (self.settings['debug'] or
            mobile in ("18088998899", "18088998898", )) \
                and verify_code == "8888":
            return True

        code = self.redis.get("yiyun:mobile:verify_code:%s" % mobile)
        return code == verify_code

    def save_verify_code(self, mobile, verify_code):

        self.redis.set("yiyun:mobile:verify_code:%s" % mobile, verify_code)

        # 30分钟内有效
        self.redis.expire("yiyun:mobile:verify_code:%s" % mobile, 1800)

    def write_error(self, status_code, **kwargs):

        if not self.is_xhr \
            and self.request.headers.get("Accept", "")\
                .lower().find("json") <= 0:
            super(ClubBaseHandler, self).write_error(status_code, **kwargs)
            return

        error_code = status_code
        error = self._reason or ""
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            log_message = None
            if isinstance(exception, BaseError):
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

        elif 'error' in kwargs:
            error = kwargs['error']

        if 'error_code' in kwargs:
            error_code = kwargs['error_code']

        self.set_status(status_code)
        self.set_header('Content-Type', 'application/json')

        chunk = {
            "error_code": error_code,
            "error": error
        }

        self.finish(chunk)

    def upload_file(self, field, to_bucket, to_key,
                    allow_exts=('jpg', 'jpeg', 'png', 'gif', 'webp')):

        """
        上传表单中指定文件到第三方并返回 key
        """

        upload_file = self.request.files.get(field)
        if not upload_file:
            raise ArgumentError(400, "没有上传")

        updload_file = self.request.files.get(field)
        return self.upload_file_to_qiniu(updload_file[0], to_bucket, to_key, allow_exts)

    def upload_file_to_qiniu(self, file, to_bucket, to_key,
                             allow_exts=('jpg', 'jpeg', 'png')):

        """
        上传指定文件到 qiniu 并返回 key
        """

        if not file:
            raise ArgumentError(400, "没有上传")

        filename = utf8(file['filename']).decode()
        if not filename or filename.split(".")[-1].lower() not in allow_exts:
            raise ArgumentError(400, "上传格式不支持")

        ext = filename.split(".")[-1].lower()
        file_body = file['body']
        if not file_body:
            raise ArgumentError(400, "上传文件为空")

        # 最大10M
        elif len(file_body) > 10485760:
            raise ArgumentError(400, "上传文件不能超过10M")

        to_key = to_key + "." + ext
        ret, info = tasks.qiniu_tool.put_data(to_bucket, to_key,
                                              file_body,
                                              check_crc=True
                                              )
        if not ret:
            self.logger.debug("上传文件到七牛失败：%s" % info)
            raise ArgumentError(500, "保存失败，请稍后重试")

        return "%s:%s" % (to_bucket, to_key)

    def url_for_page(self, page):
        """
        TODO: 待优化
        """
        query_arguments = parse_qs_bytes(self.request.query,
                                         keep_blank_values=False)
        args = []
        for key, values in query_arguments.items():
            if key == "page":
                continue

            for value in values:
                args.append((key, value))

        args.append(("page", page))
        return url_concat(self.request.path, args)

    @property
    def xhr_url_names(self):
        """
        获取所有 ajax 访问的 url
        """

        xhr_url_names = []
        for name in self.application.named_handlers:
            if name.startswith("club") and name.endswith("xhr"):
                xhr_url_names.append(name)

        return xhr_url_names

    def paginate_query(self, query, gen_pagination=True, per_page=20):
        """
        对 Query 进行分页处理

        """

        page = max(1, intval(self.get_argument('page', 1)))

        total_count = query.count()
        pages_count = int(math.ceil(total_count / per_page))

        # page = min(pages_count, page)

        query = query.paginate(page, per_page)

        if gen_pagination:
            query.pagination = Pagination(page, per_page, total_count)

        return query
