import time
import hashlib
from functools import reduce
from datetime import datetime, timedelta
from tornado.escape import parse_qs_bytes, utf8

import geohash
import tornado.escape
import tornado.web
import tornado.gen
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from peewee import JOIN_LEFT_OUTER
from wtforms import ValidationError

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import intval, decimalval
from yiyun.models import fn, User, Team, Article, ArticleCategory
from .forms.article import ArticleForm, ArticleCategoryForm


@club_app.route(r"/article/category/add", name="club_article_category_add")
class ArticleCategoryAdd(ClubBaseHandler):

    """
    添加新的文章分类
    """

    def get(self):
        form = ArticleCategoryForm()
        self.render("article/categories_create.html",
                    form=form)

    def post(self):
        form = ArticleCategoryForm(self.arguments)
        if not form.validate():
            self.render("article/categories_create.html",
                        form=form)
        else:
            category = ArticleCategory()
            form.populate_obj(category)
            category.save()
            self.redirect(self.reverse_url("club_article_categories_list"))


@club_app.route(r"/article/category/(\d+)/edit", name="club_article_category_edit")
class ArticleCategoryEdit(ClubBaseHandler):

    """
    修改文章分类
    """

    def get(self, category_id):
        category = ArticleCategory.get_or_404(id=category_id)
        form = ArticleCategoryForm(obj=category)
        self.render("article/categories_edit.html",
                    form=form)

    def post(self, category_id):
        category = ArticleCategory.get_or_404(id=category_id)

        form = ArticleCategoryForm(self.arguments)
        if not form.validate():
            self.render("article/categories_create.html",
                        form=form)
        else:
            form.populate_obj(category)
            category.save()
            self.redirect(self.reverse_url("club_article_categories_list"))


@club_app.route(r"/article/category/list", name="club_article_categories_list")
class ArticleCategoriesList(ClubBaseHandler):

    """
    文章分类列表
    """

    def get(self):
        query = ArticleCategory.select()
        query = self.paginate_query(query)
        self.render("article/categories_list.html",
                    categories=query)


@club_app.route(r"/article/category/list/action",
                name="club_article_categories_list_action")
class ArticleCategoriesListAction(ClubBaseHandler):

    """
    文章分类列表的操作
    """

    def _delete(self, category_id):
        category = ArticleCategory.get_or_404(id=category_id)
        ArticleCategory.delete()\
            .where(id=category.id)\
            .execute()
        self.write_success()

    def post(self):
        action = self.get_argument("action", "")
        id = self.get_argument("id", "")

        if action == "delete":
            self._delete(id)
        else:
            raise ArgumentError(400)


class ArticleHandlerMixin():

    def _upload_cover(self):
        pass


@club_app.route(r"/article/create", name="club_article_create")
class ArticleAdd(ClubBaseHandler):

    """
    添加新的文章
    """

    def get(self):
        form = ArticleForm(team_id=self.current_team.id)
        categories = ArticleCategory.get_all_for_choices()
        form.category.choices = categories
        self.render("article/create.html",
                    form=form)

    def post(self):
        form = ArticleForm(self.arguments, team_id=self.current_team.id)
        categories = ArticleCategory.get_all_for_choices()
        form.category.choices = categories

        if not form.validate():
            self.render("article/create.html",
                        form=form)
        else:
            article = Article()
            form.populate_obj(article)
            article.author = self.current_user.id

            if "cover" in self.request.files:
                to_bucket = self.settings['qiniu_avatar_bucket']
                to_key = "article:%s%s" % (self.current_user.id, time.time())
                to_key = hashlib.md5(to_key.encode()).hexdigest()

                cover_key = self.upload_file("cover",
                                             to_bucket=to_bucket,
                                             to_key=to_key)
                article.cover_key = cover_key

            article.save()
            self.redirect(self.reverse_url("club_articles_list"))


@club_app.route(r"/article/(\d+)/edit", name="club_article_edit")
class ArtivleEdit(ClubBaseHandler):

    """
    修改文章
    """

    def get(self, article_id):
        article = Article.get_or_404(id=article_id)

        categories = ArticleCategory.get_all_for_choices()
        form = ArticleForm(obj=article)
        form.category.choices = categories

        self.render("article/edit.html",
                    article_info=article.info,
                    form=form)

    def post(self, article_id):
        article = Article.get_or_404(id=article_id)

        categories = ArticleCategory.get_all_for_choices()
        form = ArticleForm(self.arguments)
        form.category.choices = categories

        if not form.validate():
            self.render("article/edit.html",
                        article_info=article.info,
                        form=form)

        else:
            form.populate_obj(article)

            article.last_updated_by = self.current_user.id
            article.last_updated = datetime.now()
            article.save()

            self.redirect(self.reverse_url("club_articles_list"))


@club_app.route(r"/article/list", name="club_articles_list")
class ArticlesList(ClubBaseHandler):

    """
    文章列表
    """

    def get(self):
        query = Article.select(
            Article, ArticleCategory
        ).join(
            ArticleCategory,
            JOIN_LEFT_OUTER,
            on=(Article.category == ArticleCategory.id).alias("article_category"),
        ).where(
            Article.state >= Article.DRAFT,
            Article.team_id == self.current_team.id
        )
        query = self.paginate_query(query)

        articles = []
        for item in query:
            articles.append(dict(item.list_info,
                                 category=item.article_category.info))

        self.render("article/list.html",
                    articles=articles,
                    pagination=query.pagination)


@club_app.route(r"/article/list/action", name="club_articles_list_action")
class ArticlesActionList(ClubBaseHandler):

    """
    文章列表上的操作
    """

    def _delete(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.state = Article.MARK_DELETE
        article.save()
        self.write_success()

    def _set_recommend(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.recommend = True
        article.save()
        self.write_success()

    def _unset_recommend(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.recommend = False
        article.save()
        self.write_success()

    def _set_approved(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.approved = True
        article.save()
        self.write_success()

    def _unset_approved(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.approved = False
        article.save()
        self.write_success()

    def _set_draft(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.state = Article.DRAFT
        article.save()
        self.write_success()

    def _set_published(self, article_id):
        article = Article.get_or_404(id=article_id)
        article.state = Article.PUBLISHED
        article.save()
        self.write_success()

    def post(self):
        action = self.get_argument("action", "")
        id = self.get_argument("id")

        try:
            action_handler = getattr(self, "_%s" % action)
        except AttributeError:
            self.logger.error("用户尝试不存在的 action: %s" % action)
        else:
            if not callable(action_handler):
                self.logger.error("用户尝试不存在的 action: %s" % action)
            else:
                action_handler(id)


@club_app.route(r"/article/ueditor", name="club_article_ueditor")
class ArticleUeditorConfig(ClubBaseHandler):

    """
    ueditor 配置信息
    """

    _config = {
        "imageActionName": "uploadimage",
        "imageFieldName": "upfile",
        "imageMaxSize": 2048000,
        "imageAllowFiles": [".png", ".jpg", ".jpeg", ".gif"],
        "imageCompressEnable": True,
        "imageCompressBorder": 1600,
        "imageInsertAlign": "none",
        "imageUrlPrefix": "",
        "imagePathFormat": "/ueditor/php/upload/image/{yyyy}{mm}{dd}/{time}{rand:6}",

        "scrawlActionName": "uploadscrawl",
        "scrawlFieldName": "upfile",
        "scrawlPathFormat": "/ueditor/php/upload/image/{yyyy}{mm}{dd}/{time}{rand:6}",
        "scrawlMaxSize": 2048000,
        "scrawlUrlPrefix": "",
        "scrawlInsertAlign": "none",

        "snapscreenActionName": "uploadimage",
        "snapscreenPathFormat": "/ueditor/php/upload/image/{yyyy}{mm}{dd}/{time}{rand:6}",
        "snapscreenUrlPrefix": "",
        "snapscreenInsertAlign": "none",

        "catcherLocalDomain": ["127.0.0.1", "localhost", "img.baidu.com"],
        "catcherActionName": "catchimage",
        "catcherFieldName": "source",
        "catcherPathFormat": "/ueditor/php/upload/image/{yyyy}{mm}{dd}/{time}{rand:6}",
        "catcherUrlPrefix": "",
        "catcherMaxSize": 2048000,
        "catcherAllowFiles": [".png", ".jpg", ".jpeg", ".gif"],

        "videoActionName": "uploadvideo",
        "videoFieldName": "upfile",
        "videoPathFormat": "/ueditor/php/upload/video/{yyyy}{mm}{dd}/{time}{rand:6}",
        "videoUrlPrefix": "",
        "videoMaxSize": 102400000,
        "videoAllowFiles": ["mp4"],

        "fileActionName": "uploadfile",
        "fileFieldName": "upfile",
        "filePathFormat": "/ueditor/php/upload/file/{yyyy}{mm}{dd}/{time}{rand:6}",
        "fileUrlPrefix": "",
        "fileMaxSize": 51200000,
        "fileAllowFiles": [
            ".png", ".jpg", ".jpeg", ".gif",
            ".mp4", ".webm", ".mp3", ".wav",
            ".txt", ".md"
        ],

        "imageManagerActionName": "listimage",
        "imageManagerListPath": "/ueditor/php/upload/image/",
        "imageManagerListSize": 20,
        "imageManagerUrlPrefix": "",
        "imageManagerInsertAlign": "none",
        "imageManagerAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp"],

        "fileManagerActionName": "listfile",
        "fileManagerListPath": "/ueditor/php/upload/file/",
        "fileManagerUrlPrefix": "",
        "fileManagerListSize": 20,
        "fileManagerAllowFiles": [
            ".png", ".jpg", ".jpeg", ".gif", ".bmp",
            ".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", ".mpeg", ".mpg",
            ".ogg", ".ogv", ".mov", ".wmv", ".mp4", ".webm", ".mp3", ".wav", ".mid",
            ".rar", ".zip", ".tar", ".gz", ".7z", ".bz2", ".cab", ".iso",
            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md", ".xml"
        ]
    }

    def _handler(self):
        action = self.get_argument("action", "")

        if action == "config":
            self.write(tornado.escape.json_encode(self._config))

        elif action in ["uploadvideo", "uploadimage", "uploadfile"]:
            team_id = intval(self.get_argument("team_id", ""))
            upfile = self.request.files.get("upfile", [])

            if upfile:
                file_key = ArticleHelper.get_upload_file_key(
                    self.current_user.id)
                file_bucket = self.settings["qiniu_attach_bucket"]
                qiniu_file_key = ArticleHelper.upload_image(image_file=upfile,
                                                            image_name="文章封面",
                                                            file_key=file_key,
                                                            file_bucket=file_bucket)
                self.write({
                    "state": "SUCCESS",
                    "url": Article.get_attach_urls(qiniu_file_key)["large"]
                })

        elif action == "listimage":
                        # TODO 列出已经上传的图片
            pass

        elif action == "catchimage":
            source = self.arguments["source[]"]
            images = []
            if len(source) > 0:
                file_bucket = self.settings["qiniu_attach_bucket"]
                for file_url in source:
                    try:
                        http_client = tornado.httpclient.HTTPClient()
                        response = http_client.fetch(
                            file_url, headers={"User-Agent": "Mozilla/5.0"})

                        # FIXME 文件类型转换
                        file_key = ArticleHelper.get_upload_file_key(
                            self.current_user.id)
                        qiniu_file_key = ArticleHelper.upload_to_qiniu(file_bucket=file_bucket,
                                                                       file_key=file_key,
                                                                       image_data=response.body,
                                                                       mime_type="image/jpeg")

                        images.append({"url": Article.get_cover_urls(qiniu_file_key)["large"],
                                       "source": file_url,
                                       "state": "SUCCESS"})

                    except Exception as e:
                        self.logger.error("抓取远程图片失败: %s" % e)
                        images.append({"url": "",
                                       "source": file_url,
                                       "state": "FAIL"})

            self.write({"state": "SUCCESS",
                        "list": images})

    def get(self):
        self._handler()

    def post(self):
        self._handler()
