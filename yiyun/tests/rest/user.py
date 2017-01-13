import json
import unittest
from ..base import AsyncAPITestCase
from yiyun.models import User, Sport, Team


class UserTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team]

    OBJECT_PATH = "api/2/users/{user_id}"
    USER_SELF = "api/2/users/self"

    def test_get_other_user(self):
        display_fields = ("name", "signature", "mobile", "gender", "dob",
                          "created")
        insecure_fields = ("password", "avatar_key", "pay_openid",
                           "reg_device_id", "reg_device_type")
        user = User.create(name='test')
        url = self.OBJECT_PATH.format(user_id=user.id)

        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        for field in display_fields:
            self.assertIn(field, result, field)

        for field in insecure_fields:
            self.assertNotIn(field, result, field)

    def test_get_owner_user(self):
        insecure_fields = ("password", "avatar_key", "pay_openid",
                           "reg_device_id", "reg_device_type")
        user = User.create(name='test')
        url = self.OBJECT_PATH.format(user_id=user.id)

        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())

        for field in insecure_fields:
            self.assertNotIn(field, result, field)

    def test_get_user_self(self):
        insecure_fields = ("password", "avatar_key", "pay_openid",
                           "reg_device_id", "reg_device_type")

        user = User.create(name="test user self")
        self.auth_user = user
        response = self.fetch(self.USER_SELF)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(user.id, result['id'], result)
        self.assertEqual("test user self", result["name"], result)

        for field in insecure_fields:
            self.assertNotIn(field, result, field)

    def test_patch_user(self):
        user = User.create(name="user name")
        url = self.OBJECT_PATH.format(user_id=user.id)
        body = {
            "name": "new name",
            "gender": "f",
            "dob": "1990-01-01",
            "mobule": "12345678901"
        }

        self.auth_user = user
        response = self.fetch(url, method="PATCH",
                              body=json.dumps(body),
                              headers={
                                  "Content-Type": "application/json"
                              })
        self.assertEqual(204, response.code, response.body.decode())

        updated = User.get(id=user.id)
        self.assertEqual("new name", updated.name, updated)
        self.assertEqual("f", updated.gender, updated)
        self.assertEqual("1990-01-01",
                         updated.dob.strftime("%Y-%m-%d"), updated)
        self.assertIsNone(updated.mobile, updated)


if __name__ == '__main__':
    unittest.main()
