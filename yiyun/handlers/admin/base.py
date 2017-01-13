from __future__ import division

import math
import json
from base64 import urlsafe_b64encode
from uuid import uuid4
import urllib.parse as urlparse
from urllib.parse import urlencode

import tornado.web
from tornado.httputil import url_concat
from tornado.escape import parse_qs_bytes

from yiyun.ext.routing import route
from yiyun.ext.mixins import FlashMessageMixin
from yiyun.handlers import BaseHandler
from yiyun.libs.pagination import Pagination

from yiyun.exceptions import BaseError, ArgumentError
from yiyun.models import Admin, Team
from yiyun.helpers import intval, decimalval, merge_dict
from yiyun import tasks

admin_app = route(prefix="/admin")


class AdminBaseHandler(BaseHandler, FlashMessageMixin):

    login_required = True

    def initialize(self, *args, **kwargs):
        super(AdminBaseHandler, self).initialize(*args, **kwargs)

    def get_template_namespace(self):
        namespace = super(AdminBaseHandler, self).get_template_namespace()
        namespace['merge_dict'] = merge_dict
        namespace['urlsafe_b64encode'] = urlsafe_b64encode
        return namespace

    def prepare(self):
        super(AdminBaseHandler, self).prepare()

        if self.login_required and not self.current_user:
            if self.request.method in ("GET", "HEAD"):
                url = self.get_login_url()
                if "?" not in url:
                    if urlparse.urlsplit(url).scheme:
                        next_url = self.request.full_url()
                    else:
                        next_url = self.request.uri
                    url += "?" + urlencode(dict(next=next_url))
                self.redirect(url)
                return
            raise tornado.web.HTTPError(403)

    def get_template_path(self):
        return self.application.settings.get("template_path") + "/admin"

    def get_login_url(self):
        return self.reverse_url("admin_auth_login")

    def get_current_user(self):
        admin = self.get_secure_cookie("admin")
        if not admin:
            return None

        try:
            admininfo = json.loads(admin.decode("utf-8"))
        except:
            admininfo = None

        if admininfo and admininfo.get("id", None):
            admin = Admin.get_or_none(id=admininfo['id'])

            if admin is not None:
                return admin

    @property
    def session_id(self):
        session_id = self.get_secure_cookie("session_id")
        if not session_id:
            session_id = uuid4().hex
            self.set_secure_cookie(
                "session_id", session_id, expires_days=None)

        return session_id

    def render_string(self, template_name, **kwargs):
        kwargs['url_for_page'] = self.url_for_page
        kwargs['decimalval'] = decimalval
        return super(AdminBaseHandler, self).render_string(template_name, **kwargs)

    def write_error(self, status_code, **kwargs):

        if not self.is_xhr \
            and self.request.headers.get("Accept", "")\
                .lower().find("json") <= 0:
            super(AdminBaseHandler, self).write_error(status_code, **kwargs)
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

        upload_file = self.request.files.get(field)
        if not upload_file:
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

    def url_for_page(self, page):

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
