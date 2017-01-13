import json
import unittest
from ..base import AsyncAPITestCase
from yiyun.models import User, Team, Device, UserAuthData


class AuthTestCase(AsyncAPITestCase):
    RETAIN_DATA = True
    json_header = True
    REQUIRED_MODELS = [User, Device, UserAuthData]

    def test_login_verify_code(self):
        user = User.create(name='test', mobile="13838003801")

        url = "api/2/auth/login_verify_code"
        body = {
            "mobile": "13838003801",
            "verify_code": "8888"
        }

        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("session", result, result)
        self.assertIn("current_user", result, result)

    def test_login(self):
        user = User.create(
            name='test2',
            mobile="13838003802",
            password=User.create_password("123456")
        )

        url = "api/2/auth/login"
        body = {
            "username": "13838003802",
            "password": "123456"
        }

        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("session", result, result)
        self.assertIn("current_user", result, result)

    def test_refresh_token(self):
        self.auth_user = User.create(
            name='test3',
            mobile="13838003803",
            password=User.create_password("123456")
        )

        url = "api/2/auth/refresh_token"

        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("session", result, result)
        self.assertIn("current_user", result, result)

    def test_reset_password(self):
        user = User.create(
            name='test4',
            mobile="13838003804",
            password=User.create_password("123456")
        )

        new_password = "654321"
        url = "api/2/auth/reset_password"
        body = {
            "username": "13838003804",
            "verify_code": "8888",
            "new_password": new_password
        }

        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(200, response.code, response.body.decode())

        user = User.get(id=user.id)
        result = User.check_password(user.password, new_password)
        self.assertEqual(True, result, result)


if __name__ == '__main__':
    unittest.main()
