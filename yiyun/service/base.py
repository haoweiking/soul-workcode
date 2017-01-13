"""
base service
"""

from yiyun.models import BaseModel


class ServiceException(Exception):
    pass


class BaseService(object):
    database = BaseModel._meta.database
