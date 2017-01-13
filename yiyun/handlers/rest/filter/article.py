"""
文章 filter
"""

from yiyun.libs.peewee_filter import (Filter, Filtering, NumberFiltering,
                                      SoftForeignKeyFiltering)
from yiyun.models import ArticleCategory


class ArticleFilter(Filter):
    team_id = NumberFiltering(source="team_id")
    category = SoftForeignKeyFiltering(source=ArticleCategory,
                                       foreign_field="name",
                                       function="regexp")

    class Meta:
        fields = ("team_id", "category")
