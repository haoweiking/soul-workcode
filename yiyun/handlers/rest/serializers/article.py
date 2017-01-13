from yiyun.libs.peewee_serializer import Serializer, SerializerField
from yiyun.core import current_app as app
from yiyun.models import Article, ArticleCategory


class ArticleCategorySerializer(Serializer):
    class Meta:
        only = (ArticleCategory.id, ArticleCategory.name,)


class ArticleSimpleSerializer(Serializer):
    category = SerializerField(source="get_category")
    cover = SerializerField(source="get_cover_url")

    class Meta:
        exclude = (Article.category, Article.text)

    def get_category(self, obj=None):
        obj = self.instance or obj
        if not hasattr(obj, "article_category") or not obj.article_category.id:
            return {}
        return ArticleCategorySerializer(instance=obj.article_category).data

    def get_cover_url(self, obj=None):
        obj = self.instance or obj  # type: Article
        # cover_url = app.settings["attach_url"]
        cover_url = app.settings["cover_url"]
        return obj.get_cover_urls(obj.cover_key, cover_url)


class ArticleSerializer(ArticleSimpleSerializer):
    pass
