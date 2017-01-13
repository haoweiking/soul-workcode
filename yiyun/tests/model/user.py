#!/usr/bin/env python


"""
User 单元测试, 包括 CRUD
TODO: 现在的 TestCase 还是不太方便
"""

from tornado.testing import unittest

from yiyun.models import User
from ..base import AsyncModelTestCase


class UserTestCase(AsyncModelTestCase):
    REQUIRED_MODELS = [User]

    def test_create(self):
        """
        测试创建用户
        实际并不迫切需要此测试
        """
        user = User.create(
            name='test_user',
            mobile=13800138000
        )
        _user = User.get(User.mobile == 13800138000)

        self.assertEqual(user.id, _user.id)

    def test_delete_user(self):
        user = User.create(
            name='will be deleted'
        )
        _user = User.get(id=user.id)
        _user.delete_instance()


if __name__ == '__main__':
    unittest.main()
