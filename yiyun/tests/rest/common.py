import unittest
from yiyun.models import User
from ..base import AsyncAPITestCase


class RequestQiniuTokenTestCase(AsyncAPITestCase):
    REQUIRED_MODELS = [User]
    PATH = "api/2/common/qiniu/upload_token"

    # def test_get_token(self):
    #     user = User.create(name='test')
    #     params = {"type": "activity_cover"}

    #     self.auth_user = user
    #     response = self.fetch(self.PATH, params=params)
    #     self.assertEqual(200, response.code, response.body)

    def test_api_signature():
        pass

if __name__ == '__main__':
    unittest.main()
