"""
Article service
"""

from peewee import SelectQuery, JOIN

from .base import BaseService
from yiyun.models import Article, ArticleCategory


class ArticleService(BaseService):

    @classmethod
    def list(cls) -> SelectQuery:
        """
        获取已发布的文章列表
        :return:
        """
        query = Article.select(Article, ArticleCategory)\
            .join(ArticleCategory, join_type=JOIN.LEFT_OUTER,
                  on=(Article.category == ArticleCategory.id).alias("article_category"))\
            .where(Article.approved == True,
                   Article.state == Article.PUBLISHED)
        return query

    @classmethod
    def get_article(cls, article_id: int):
        query = Article.select(Article, ArticleCategory) \
            .join(ArticleCategory, join_type=JOIN.LEFT_OUTER,
                  on=(Article.category == ArticleCategory.id).alias("article_category")) \
            .where(Article.id == article_id)
        return query.get()
