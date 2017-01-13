"""
文章 API
"""

from .base import (rest_app, BaseClubAPIHandler, ApiException, authenticated,
                   validate_arguments_with)
from yiyun.models import Article
from yiyun.service.article import ArticleService
from .serializers.article import ArticleSimpleSerializer, ArticleSerializer
from .filter.article import ArticleFilter


@rest_app.route(r"/articles")
class ArticlesHandler(BaseClubAPIHandler):
    """
    article Model level handler
    """
    login_required = False
    filter_classes = (ArticleFilter,)

    def get(self):
        query = ArticleService.list()
        filtered = self.filter_query(query)
        page = self.paginate_query(filtered)
        data = self.get_paginated_data(page=page, alias="articles",
                                       serializer=ArticleSimpleSerializer)
        self.write(data)


@rest_app.route(r"/articles/(\d+)")
class ArticleObjectHandler(BaseClubAPIHandler):
    """
    文章详情
    """

    login_required = False

    def get_obj(self, article_id: int):
        try:
            return ArticleService.get_article(article_id)
        except Article.DoesNotExist:
            raise ApiException(404, "对象不存在")

    def is_published(self, article: Article):
        """文章是否发布"""
        if article.state != Article.PUBLISHED:
            raise ApiException(422, "文章尚未发布")
        elif not article.approved:
            raise ApiException(422, "正在审核中")
        return True

    def get(self, article_id):
        obj = self.get_obj(article_id)

        # add article's views_count
        obj.views_count += 1
        obj.save()

        self.is_published(article=obj)
        data = ArticleSerializer(instance=obj).data
        self.write(data)
