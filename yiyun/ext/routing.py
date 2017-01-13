#!/usr/bin/env python

"""
    extensions.route

    Example:
    @route(r'/', name='index')
    class IndexHandler(tornado.web.RequestHandler):
        pass

    class Application(tornado.web.Application):
        def __init__(self):
            handlers = [
                # ...
            ] + Route.routes()
"""

from tornado.web import url
from functools import reduce


class Route(object):

    _routes = {}

    def __init__(self, pattern=None, kwargs=None, name=None, host='.*$',
                 prefix="", module=None):

        self.pattern = pattern
        self.kwargs = kwargs if kwargs else {}
        self.name = name
        self.host = host

        self.prefix = prefix
        self.module = module

    def __call__(self, handler_class):
        spec = url(self.pattern, handler_class, self.kwargs, name=self.name)
        spec.host = self.host
        self._routes.setdefault(self.host, []).append(spec)
        return handler_class

    def route(self, pattern=None, kwargs=None, name=None, host='.*$'):

        self.pattern = pattern
        self.kwargs = kwargs if kwargs else {}
        self.name = name

        if host != ".*$":
            self.host = host

        if self.prefix:
            self.pattern = self.prefix + self.pattern

        if not self.name:
            self.name = self.pattern.strip("/").replace("/", "_")

        return self

    @classmethod
    def routes(cls, application=None):
        if application:
            for host, handlers in cls._routes.items():
                application.add_handlers(host, handlers)
        else:
            return reduce(lambda x, y: x + y, list(cls._routes.values())) \
                if cls._routes else []

    @classmethod
    def url_for(cls, name, *args):
        named_handlers = dict([(spec.name, spec)
                               for spec in cls.routes() if spec.name])

        if name in named_handlers:
            return named_handlers[name].reverse(*args)
        raise KeyError("%s not found in named urls" % name)


route = Route
