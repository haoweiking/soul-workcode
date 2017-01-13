#!/usr/bin/env python
# coding: utf-8

import os
import time
import importlib
import logging
import hashlib
import hmac
import base64

from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, AsyncHTTPClient
from tornado.ioloop import IOLoop

from tornado.escape import urllib_parse

from yiyun import create_app
from yiyun.helpers import setting_from_object, create_token
from yiyun import settings as config
from yiyun.models import Client
from yiyun.libs.parteam import ParteamUser

try:
    import unittest_settings
except ImportError:
    unittest_settings = None

try:
    import local_settings
except ImportError:
    local_settings = None


def reject_settings(prefix='test_'):
    """
    设置测试用的数据库名 DB_NAME
    :param prefix: 测试用数据库前缀
    :return: settings
    """
    settings = setting_from_object(config)

    if unittest_settings:
        settings.update(setting_from_object(unittest_settings))

    if local_settings:
        settings.update(setting_from_object(local_settings))
        if not settings["db_name"].startswith(prefix):
            settings['db_name'] = prefix + settings['db_name']

    return settings


def initial_database():
    """
    初始化数据库,
    重建旧表
    创建表
    Returns:

    """
    # TODO: 重复代码抽象

    from yiyun.helpers import find_subclasses
    from yiyun.models import BaseModel, Sport, User, Team, Activity

    # drop old database and create new;
    test_settings = reject_settings()
    test_db = test_settings['db_name']

    raw_sql = ("drop database {test_db};"
               "create database {test_db};"
               "use {test_db};")

    # create new tables
    BaseModel._meta.database.execute_sql(raw_sql.format(test_db=test_db))

    models = find_subclasses(BaseModel)

    if not Sport.table_exists():
        Sport.create_table()

    if not User.table_exists():
        User.create_table()

    if not Team.table_exists():
        Team.create_table()

    if not Activity.table_exists():
        Activity.create_table()

    for model in models:
        if model._meta.db_table.startswith("__"):
            logging.debug(("table skip: " + model._meta.db_table))
        elif model.table_exists():
            logging.debug(('table exist: ' + model._meta.db_table))
        else:
            model.create_table()
            logging.debug(('table created: ' + model._meta.db_table))

    logging.debug('create all [ok]')


app, client = None, None


def get_current_app():
    """ 整个测试过程使用唯一的app
    """

    global app

    if app is None:
        app = create_app(reject_settings(), use_db_pool=False)

        # # 创建 app 后初始化所有数据库表
        # initial_database()

        # 修改数据库编码格式（runner中默认编码是latin1）
        app.db.execute_sql("ALTER DATABASE %s CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" %
                           app.settings['db_name'])

    return app


def get_current_client():

    global client

    if client is None:

        if not Client.table_exists():
            Client.create_table()

        client = Client.create(name='test_doctor',
                               key=create_token(16),
                               secret=create_token(32),
                               verify_sign=True
                               )

    return client


class BaseTestCase(AsyncTestCase):
    """docstring for BaseTestCase"""

    def get_url(self, path, format="json", **kwargs):

        url = "http://example.com/1/" + path

        all_args = {}
        all_args.update({'format': format})

        if kwargs:
            all_args.update(kwargs)

        url += '?' + urllib_parse.urlencode(all_args)

        return url

    def get_client(self):

        return AsyncHTTPClient(self.io_loop)


class ModelTestMixin(object):
    """
    :attr bool RETAIN_DATA: 是否保留测试数据, 默认不保留, 保留数据可以方便调试, 但目前
        会被其它 class 运行前清楚
    :attr list REQUIRED_MODELS: 单元测试所依赖的 Model, 需要按照外键依赖顺序添加
        如: [User, Team] 可正常运作, 但 [Team, User] 将会报错, 因为创建 Team 的时候
        依赖了 User 作为外键
    """
    RETAIN_DATA = False
    REQUIRED_MODELS = []

    def __init__(self, *args, **kwargs):
        self.app = self.get_app()
        self.app.db.connect()

        super(ModelTestMixin, self).__init__(*args, **kwargs)

    def setUp(self):
        if self.app.db.is_closed():
            self.app.db.connect()
        super(ModelTestMixin, self).setUp()

    def get_app(self):
        return get_current_app()

    @classmethod
    def _modelNameToModule(cls, modelName):
        module = importlib.import_module("yiyun.models")

        if isinstance(modelName, str):
            return getattr(importlib.import_module("yiyun.models"), modelName)
        elif issubclass(modelName, module.BaseModel):
            return modelName

    @classmethod
    def _walkThrough(cls, modelNames, func, reverse):
        if reverse:
            modelNames.reverse()

        for modelName in modelNames:
            model = cls._modelNameToModule(modelName)
            try:
                func(model)
            except Exception as e:
                print(e)

        if reverse:
            # 还原顺序
            modelNames.reverse()

    @classmethod
    def _setUpClass(cls, modelNames, dropOldTable=False):

        # 数据模型如果有修改 则设置 dropOldTable=True 重新
        # 生成 table

        assert isinstance(modelNames, (list, tuple)), \
            'param "modelNames" must be a list or tuple'

        if dropOldTable:
            cls._walkThrough(modelNames,
                             lambda model: model.drop_table(
                                 fail_silently=True, cascade=True)
                             if model.table_exists() else None, True)

        cls._walkThrough(modelNames,
                         lambda model: model.create_table(fail_silently=True), False)

    @classmethod
    def _tearDownClass(cls):
        if not cls.RETAIN_DATA:
            cls.drop_tables()

    def _tearDown(self, modelNames=None):
        """
        每个测试结束后清空测试数据, 保留表
        Args:
            modelNames:

        Returns:

        """
        models = self.REQUIRED_MODELS if not modelNames else modelNames
        self.truncate_tables(models=models)

    @classmethod
    def drop_tables(cls):
        """
        清空测试数据,
        如果 RETAIN_DATA == True, 不清空
        Returns:

        """
        if not cls.RETAIN_DATA:
            cls._drop_tables(models=cls.REQUIRED_MODELS)

    @classmethod
    def _drop_tables(cls, models):
        # cls._walkThrough(modelNames,
        #                  lambda model: model.drop_table(fail_silently=True,
        #                                                 cascade=True)
        #                  if model.table_exists() else None, True)
        prefix = "SET FOREIGN_KEY_CHECKS = 0;"
        suffix = "SET FOREIGN_KEY_CHECKS = 1;"
        pre_delete_tables = []
        for index, modelName in enumerate(models):
            model = cls._modelNameToModule(modelName)
            table_name = model._meta.db_table
            pre_delete_tables.append("DROP TABLE `{table}`;"
                                     .format(table=table_name))

            if index + 1 == len(models):
                sql = prefix + ''.join(pre_delete_tables) + suffix
                model._meta.database.execute_sql(sql)

    @classmethod
    def truncate_tables(cls, models):
        """
        清空 table
        Args:
            models:

        Returns:

        """
        prefix = "SET FOREIGN_KEY_CHECKS = 0;"
        suffix = "SET FOREIGN_KEY_CHECKS = 1;"
        pre_delete_tables = []
        for index, modelName in enumerate(models):
            model = cls._modelNameToModule(modelName)
            table_name = model._meta.db_table
            pre_delete_tables.append("TRUNCATE {table};"
                                     .format(table=table_name))

            if index == len(models):
                sql = prefix + ''.join(pre_delete_tables) + suffix
                model._meta.database.execute_sql(sql)


class ApiBaseTestCase(AsyncHTTPTestCase):
    """docstring for ApiBaseTestCase"""

    def __init__(self, methodName='runTest', **kwargs):
        self.auth_user = None
        self.app = self.get_app()
        super(ApiBaseTestCase, self).__init__(methodName=methodName, **kwargs)

    def setUp(self):
        if self.app.db.is_closed():
            self.app.db.connect()
        super(ApiBaseTestCase, self).setUp()

    def get_app(self):
        return get_current_app()

    def get_url(self, path, format="json", **kwargs):
        """Returns an absolute url for the given path on the test server."""

        url = '%s://localhost:%s/%s' % (self.get_protocol(),
                                        self.get_http_port(), path)

        all_args = {}
        if hasattr(self, '_params'):
            all_args.update(self._params)

        if kwargs:
            all_args.update(kwargs)

        url += '?' + urllib_parse.urlencode(all_args)

        return url

    def get_new_ioloop(self):
        return IOLoop.instance()

    @property
    def client(self):
        """
        获取一个用来测试的 ihealth.models.Client
        """

        if not hasattr(self, "_client"):
            self._client = self._get_client()

        return self._client

    def _get_client(self):

        return get_current_client()

    def get_headers(self):
        """
        http request headers
        Returns: dict

        """
        headers = {
            'X-Api-Key': self.client.key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Timestamp': str(int(time.time() * 1000)),
            'X-Nonce': create_token(32)
        }

        # 添加登录信息
        if self.auth_user:
            if isinstance(self.auth_user, ParteamUser):
                access_token = self.auth_user.ptToken
            else:
                access_token = self.auth_user.generate_auth_token()
            headers['X-Access-Token'] = access_token
        return headers

    def generate_signature(self, path, headers=None, **kwargs):

        content_type = headers.get("Content-Type", "")
        timestamp = headers.get("X-Timestamp", "")
        nonce = headers.get("X-Nonce", "")
        body = kwargs.get("body", "")
        method = kwargs.get("method", "get")

        signature = ""
        if self.client.verify_sign:
            arguments = []
            if hasattr(self, '_params'):
                for k, v in self._params.items():
                    v = str(v)
                    if v.strip():
                        arguments.append("%s=%s" % (k, v))

            arguments = sorted(arguments)

            json_body = ""
            if content_type.endswith("json") and body:
                json_body = base64.b64encode(body.strip().encode()).decode()

            string_to_sign = "%s/%s%s%s%s%s" % (
                method.upper(), path, "&".join(arguments), json_body,
                timestamp, nonce)

            hmac_hash = hmac.new(self.client.secret.encode(),
                                 string_to_sign.encode(),
                                 digestmod=hashlib.sha256
                                 ).digest()

            signature = base64.b64encode(hmac_hash)

        return signature

    def fetch(self, path, **kwargs):
        headers = self.get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # url params
        if 'params' in kwargs:
            self._params = kwargs.pop('params')

        signature = self.generate_signature(path, headers, **kwargs)
        if signature:
            headers['X-Signature'] = signature

        kwargs.update(headers=headers)

        return super(ApiBaseTestCase, self).fetch(path, **kwargs)


class AsyncAPITestCase(ModelTestMixin, ApiBaseTestCase):
    """
    :attr bool COOKIE_AUTHORIZED: 使用 cookie 传输登录信息
    :attr bool json_header: 使用 'application/json' 调用接口
    """
    COOKIE_AUTHORIZED = False
    json_header = False

    @classmethod
    def setUpClass(cls):
        if cls.REQUIRED_MODELS:
            cls._setUpClass(modelNames=cls.REQUIRED_MODELS, dropOldTable=True)
        super(AsyncAPITestCase, cls).setUpClass()

    def get_headers(self):
        headers = super(AsyncAPITestCase, self).get_headers()

        if self.json_header:
            headers['Content-Type'] = 'application/json'

        return headers

    @classmethod
    def tearDownClass(cls):
        cls._tearDownClass()
        super(AsyncAPITestCase, cls).tearDownClass()

    def tearDown(self):
        self._tearDown()
        super(AsyncAPITestCase, self).tearDown()


class AsyncModelTestCase(ModelTestMixin, AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        if cls.REQUIRED_MODELS:
            cls._setUpClass(modelNames=cls.REQUIRED_MODELS, dropOldTable=True)
        super(AsyncModelTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls._tearDownClass()
        super(AsyncModelTestCase, cls).tearDownClass()

    def tearDown(self):
        self._tearDown()
        super(AsyncModelTestCase, self).tearDown()
