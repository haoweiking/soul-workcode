import copy
from datetime import datetime, date
from decimal import Decimal
import json

from wtforms import validators
from peewee import fn, Model
from peewee import (BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured)

from playhouse.shortcuts import model_to_dict, dict_to_model

from yiyun.ext.database import (ListField, TextListField, PointField, GeoHashField, JSONField,
                                JSONTextField, PasswordField)
from yiyun.helpers import JSONEncoder

from yiyun.core import db
from yiyun.core import current_app as app
from yiyun.exceptions import Http404


class BaseModel(Model):

    class Meta:
        database = db

    @classmethod
    def get_or_404(cls, *args, **kwargs):
        try:
            return cls.get(**kwargs)
        except cls.DoesNotExist:
            raise Http404()

    @classmethod
    def get_or_none(cls, *args, **kwargs):
        try:
            return cls.get(**kwargs)
        except cls.DoesNotExist:
            return None

    @classmethod
    def from_dict(cls, data: dict):
        return dict_to_model(cls, data)

    def to_dict(self, only=None, exclude=None, to_json=True):

        if to_json:
            model = copy.deepcopy(self)

            for field_name, field in self._meta.fields.items():
                if self._data.get(field.name) is not None:
                    continue

                if isinstance(field, (ListField, TextListField)):
                    setattr(model, field.name, [])

                elif isinstance(field, (JSONField, JSONTextField)):
                    setattr(model, field.name, {})

                elif isinstance(field, (CharField, DateTimeField, DateField)):
                    setattr(model, field.name, "")

                elif isinstance(field, (IntegerField, BigIntegerField)):
                    setattr(model, field.name, 0)

                elif isinstance(field, (DecimalField, FloatField, DoubleField)):
                    setattr(model, field.name, 0.0)
        else:
            model = self

        return model_to_dict(model, only=only, exclude=exclude)

    def to_json(self, only=None, exclude=None):
        return json.dumps(self.to_dict(only, exclude, to_json=True), cls=JSONEncoder)

    @property
    def info(self):
        if not hasattr(self, '_info'):
            self._info = self.to_dict()

            if hasattr(self, 'avatar_key'):
                pass

            elif hasattr(self, 'cover_key'):
                pass

        return self._info

    @classmethod
    def get_cover_urls(cls, cover_key, cover_url=None, crop=True):

        url = ""
        if cover_key:
            if cover_url is None:
                cover_url = app.settings['avatar_url']

            cover_key = cover_key.split(":")[-1]
            url = "{0}/{1}".format(cover_url, cover_key) if cover_key else ""

        if crop:
            sizes = ["!c256", "!c512", "!c1024"]  # 按指定尺寸裁剪
        else:
            sizes = ["!t256", "!t512", "!t1024"]  # 按指定尺寸缩略图，不裁剪

        return {
            "url": url,
            "sizes": sizes
        }

    def get_cover_url(self, cover_key=None, size="large", crop=True):

        if size not in ("large", "medium", "small", "origin"):
            size = "large"

        if cover_key is None:
            if hasattr(self, "avatar_key"):
                cover_key = self.avatar_key

            elif hasattr(self, "cover_key"):
                cover_key = self.cover_key

        if not cover_key:
            return ""

        if crop:
            suffixes = {
                "origin": "",
                "large": "!c1024",
                "medium": "!c512",
                "small": "!c256"
            }
        else:
            suffixes = {
                "origin": "",
                "large": "!t1024",
                "medium": "!t512",
                "small": "!t256"
            }

        cover_url = app.settings['avatar_url']
        cover_key = cover_key.split(":")[-1]

        return "%s/%s%s" % (cover_url, cover_key, suffixes[size])

    @classmethod
    def get_attach_url(cls, cover_key, crop=False):

        if not cover_key:
            return {}

        cover_url = app.settings['attach_url']
        cover_key = cover_key.split(":")[-1]

        return {
            "url": "%s/%s" % (cover_url, cover_key),
        }


class Unique(object):

    """ validator that checks field uniqueness """

    def __init__(self, model, field, message=None):
        self.model = model
        self.field = field
        if not message:
            message = 'This field already exists'
        self.message = message

    def __call__(self, form, field):

        check = self.model.select().where(self.field == field.data).exists()
        if check:
            raise validators.ValidationError(self.message)
