"""
文章接口单元测试
"""
import json
from random import randint
from tornado.testing import unittest
from mixer.backend.peewee import mixer

from yiyun.tests.base import AsyncAPITestCase
from yiyun.models import Team, Article, ArticleCategory


class ArticleTestCase(AsyncAPITestCase):
    RETAIN_DATA = True
    ARTICLES_LIST = "api/2/articles"
    DETAIL_PATH = ARTICLES_LIST + "/{article.id}"

    REQUIRED_MODELS = [ArticleCategory, Article]

    def test_list_articles(self):
        total_count = randint(1, 10)

        for _ in range(0, total_count):
            mixer.blend(Article, state=Article.PUBLISHED, approved=True)

        response = self.fetch(self.ARTICLES_LIST)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        for article in result["articles"]:
            self.assertEqual(article["state"], Article.PUBLISHED,
                             "未发布文章不应该输出")
            self.assertTrue(article["approved"], "未审核的文章不应该输出")

    def test_get_articles_with_team(self):
        total_count = randint(1, 10)
        team_id = randint(1, 1000)
        for _ in range(0, total_count):
            mixer.blend(Article, state=Article.PUBLISHED, approved=True,
                        team_id=team_id)
            mixer.blend(Article, state=Article.PUBLISHED, approved=True)

        response = self.fetch(self.ARTICLES_LIST, params={"team_id": team_id})
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        for article in result["articles"]:
            self.assertEqual(article["state"], Article.PUBLISHED,
                             "未发布文章不应该输出")
            self.assertTrue(article["approved"], "未审核的文章不应该输出")

    def test_get_articles_with_category(self):
        total_count = randint(1, 10)
        category = mixer.blend(ArticleCategory, name="test_category")
        for _ in range(0, total_count):
            mixer.blend(Article, state=Article.PUBLISHED, approved=True,
                        category=category.id)
        response = self.fetch(self.ARTICLES_LIST,
                              params={"category": category.name})
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertTrue(len(result["articles"]) > 0, "返回文章列表为空")
        for article in result["articles"]:
            _category = article["category"]
            self.assertRegex(_category["name"], r"{0}".format(category.name),
                             "获取到非指定分类")

    def test_get_article_obj(self):
        category = mixer.blend(ArticleCategory)
        article = mixer.blend(Article, category=category.id,
                              state=Article.PUBLISHED, approved=True)

        url = self.DETAIL_PATH.format(article=article)
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())

    def test_get_article_obj_not_published(self):
        category = mixer.blend(ArticleCategory)
        article = mixer.blend(Article, category=category.id,
                              state=Article.DRAFT)
        url = self.DETAIL_PATH.format(article=article)
        response = self.fetch(url)
        self.assertEqual(422, response.code, "获取到未发布文章")

        article = mixer.blend(Article, category=category.id, approved=False)
        url = self.DETAIL_PATH.format(article=article)
        response = self.fetch(url)
        self.assertEqual(422, response.code, "获取到审核中的文章")


if __name__ == '__main__':
    unittest.main()
