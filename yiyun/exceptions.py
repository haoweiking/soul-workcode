#!/usr/bin/env python

from tornado.web import HTTPError


class BaseError(Exception):
    """Base Error"""

    status_code = 400
    error_code = None
    message = ""
    log_message = ""

    def __init__(self, error_code, message, log_message=None,
                 status_code=None, payload=None):

        super(Exception, self).__init__()

        self.message = message
        if status_code is not None:
            self.status_code = status_code

        elif error_code >= 400 and error_code <= 599:
            self.status_code = error_code

        self.error_code = error_code
        self.payload = payload
        self.log_message = log_message

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['error_code'] = self.error_code or self.status_code
        return rv


class ArgumentError(BaseError):
    """Arguments error"""

    pass


class ConfigError(BaseError):
    """raise config error"""

    pass


class UrlError(BaseError):
    """route write error"""

    pass


class NotCallableError(BaseError):
    """callable error"""

    pass


class Http404(HTTPError):

    def __init__(self, log_message='not found', *args, **kwargs):
        super(Http404, self).__init__(404, log_message, *args, **kwargs)


class HttpForbiddenError(HTTPError):

    def __init__(self, log_message='forbidden', *args, **kwargs):
        super(HttpForbiddenError, self).__init__(403, log_message, *args, **kwargs)


class HttpNotAllowError(HTTPError):

    def __init__(self, log_message='method not allowed', *args, **kwargs):
        super(HttpNotAllowError, self).__init__(405, log_message, *args, **kwargs)


class HttpBadRequestError(HTTPError):

    def __init__(self, log_message='bad request', *args, **kwargs):
        super(HttpBadRequestError, self).__init__(400, log_message, *args, **kwargs)


class Http500(HTTPError):

    def __init__(self, log_message='server error', *args, **kwargs):
        super(Http500, self).__init__(500, log_message, *args, **kwargs)
