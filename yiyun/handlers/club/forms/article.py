import wtforms
from wtforms import Form, validators, ValidationError
from wtforms import fields as f
from wtfpeewee.orm import model_form
from wtfpeewee.fields import ModelSelectField

from yiyun.ext.database import WPSelectField
from yiyun.models import Team, Sport, ChinaCity, Article, ArticleCategory
from yiyun.ext.forms import Form, FileField, file_required, file_allowed,\
                            TextAreaField


article_exclude = ("id", "created", "created_by", "updated", "last_updated_by", "state",
                   "approved", "recommend", "cover_key", "views_count")
ArticleForm = model_form(Article, base_class=Form, field_args={},
                         exclude=article_exclude)
ArticleForm.category = wtforms.fields.SelectField("分类", choices=[])
ArticleForm.cover = wtforms.fields.FileField("封面")
ArticleForm.team_id = wtforms.fields.HiddenField("俱乐部")


category_exclude = ("id", "articles_count")
ArticleCategoryForm = model_form(ArticleCategory, base_class=Form,
                                 field_args={}, exclude=category_exclude)
