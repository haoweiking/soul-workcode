from datetime import datetime
from .base import BaseModel
from yiyun.core import current_app as app
from peewee import (CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured,
                    CompositeKey, IntegrityError)

from yiyun.ext.database import ListField


class ArticleCategory(BaseModel):

    """
    文章分类
    """

    class Meta:
        db_table = 'article_category'

    name = CharField(max_length=100, unique=True, index=True,
                     verbose_name="分类名称")
    articles_count = IntegerField(default=0, verbose_name="分类文章数量")

    @classmethod
    def get_all(cls):
        # 获取全部的文章分类列表

        query = cls.select()

        categories = []
        for article_category in query:
            categories.append(article_category.info)

        return categories

    @classmethod
    def get_all_for_choices(cls):
        # 获取全部的文章分类选项，在 form 中使用

        article_categories = cls.get_all()

        categories_for_choices = [("0", "默认")]
        for article_category in article_categories:
            str_id = str(article_category['id'])
            categories_for_choices.append((str_id, article_category['name']))

        return categories_for_choices


class Article(BaseModel):

    """
    文章
    """

    class Meta:
        db_table = 'article'
        order_by = ("-created", "-id")

    MARK_DELETE = -1
    DRAFT = 1
    PUBLISHED = 2

    STATE = (
        (MARK_DELETE, "删除"),
        (DRAFT, "草稿"),
        (PUBLISHED, "已发布")
    )

    team_id = IntegerField(verbose_name="俱乐部", help_text="俱乐部 Team.id",
                           default=0)
    cover_key = CharField(default="", max_length=128)
    title = CharField(max_length=255, verbose_name="标题")
    summary = TextField(verbose_name="摘要")
    text = TextField(verbose_name="内容")
    approved = BooleanField(default=False, verbose_name="是否通过审核")
    recommend = BooleanField(default=False, verbose_name="是否推荐")
    state = IntegerField(default=1, verbose_name="状态")
    category = IntegerField(default=0, verbose_name="分类")
    views_count = IntegerField(default=0, verbose_name="浏览量")

    created_by = IntegerField(default=0)
    last_updated_by = IntegerField(default=0)
    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)

    @property
    def info(self):
        if not hasattr(self, "_info"):
            self._info = self.to_dict(exclude=[Article.cover_key])
            cover_url = app.settings["attach_url"]
            self._info["cover"] = Article.get_cover_urls(self.cover_key,
                                                         cover_url=cover_url)

        return self._info

    @property
    def public_info(self):
        if not hasattr(self, "_public_info"):
            self._public_info = self.to_dict(
                exclude=[Article.cover_key]
            )
            cover_url = app.settings["attach_url"]
            self._public_info["cover"] = \
                Article.get_cover_urls(self.cover_key,
                                       cover_url=cover_url)

        return self._public_info

    @property
    def list_info(self):
        if not hasattr(self, "_list_info"):
            self._list_info = self.to_dict(
                exclude=[Article.cover_key, Article.text]
            )
            cover_url = app.settings["attach_url"]
            self._list_info["cover"] = \
                Article.get_cover_urls(self.cover_key,
                                       cover_url=cover_url)

        return self._list_info
