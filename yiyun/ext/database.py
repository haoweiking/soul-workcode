#!/usr/bin/env python


import logging
import json
import geohash

from playhouse.shortcuts import RetryOperationalError
from peewee import MySQLDatabase, fn, Field
from peewee import (BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured)

from wtforms import fields as f
from wtforms import widgets
from wtforms.compat import text_type
from wtforms.validators import ValidationError

from wtfpeewee.fields import StaticAttributesMixin

from wtfpeewee.fields import WPDateField
from wtfpeewee.fields import WPDateTimeField
from wtfpeewee.fields import WPTimeField
from wtfpeewee.orm import ModelConverter as ModelConverter_

_logger = logging.getLogger("yiyun")


class PointField(Field):
    db_field = 'point'

    def db_value(self, value):
        return value

    def python_value(self, value):
        return value


class PasswordField(CharField):
    pass


class ListField(TextField):

    """docstring for ListField"""

    def db_value(self, value):
        if value and not isinstance(value, (list, tuple)):
            raise ValueError('The field "{field}" must be a tuple or list, '
                             '{value} given'
                             .format(field=self.name, value=value))
        return ",".join(value)

    def python_value(self, value):
        return value.split(",") if value else []


class TextListField(TextField):

    def db_value(self, value):
        return json.dumps(value, separators=(',', ':'), ensure_ascii=False) \
            if value is not None and value != "" else None

    def python_value(self, value):
        try:
            value = json.loads(value) if value and value != "" else None
            if isinstance(value, str):
                value = [value]

            return value

        except Exception:
            return value


class GeoHashField(CharField):

    def db_value(self, value):

        if not isinstance(value, (list, tuple)) or len(value) < 2:
            return ""

        return geohash.encode(float(value[0]), float(value[1]))


class JSONField(CharField):

    """VARCHAR fields have max length of 255 (mysql < 5.0.3) or 65,535. The
    default is 255 and can be changed by passing desired max to constructor.
    """

    def db_value(self, value):
        return None if value is None or value == "" else json.dumps(value, separators=(',', ':'))

    def python_value(self, value):
        return json.loads(value) if value else value


class JSONTextField(TextField):

    """TEXT fields have a max length of 65535 characters"""

    def db_value(self, value):
        return json.dumps(value, separators=(',', ':')) if value is not None and value != "" else None

    def python_value(self, value):
        try:
            return json.loads(value) if value and value != "" else None
        except Exception:
            return value


def Point(lat, lng):
    return fn.PointFromText("Point(%s %s)" % (lat, lng))


def Polygon(a1, a2, b1, b2, c1, c2, d1, d2):
    return fn.PolyFromText('POLYGON((%s %s, %s %s, %s %s, %s %s))' % (a1, a2, b1, b2, c1, c2, d1, d2))


def Distance(p1, p2):
    """
    mysql 距离计算工式
    对应sql: round(glength(linestringfromwkb(linestring(asbinary(a), asbinary(b)))))
    """
    # return fn.round(fn.ST_Distance(p1, p2)*100, 6)
    return fn.round(fn.glength(fn.linestringfromwkb(fn.linestring(p1, p2))) * 100, 6)


def ST_Within(p1, xy1, xy2):
    # envelope(linestring(point(@rlon1, @rlat1), point(@rlon2, @rlat2)))
    return fn.ST_Within(p1, fn.envelope(fn.linestring(xy1, xy2)))

# 注册点类型
MySQLDatabase.register_fields({'point': 'point'})


class RetryMySQLDatabase(RetryOperationalError, MySQLDatabase):
    pass


class TextListWidget(object):

    def __call__(self, field, **kwargs):
        html = []
        for subfield in field:
            html.append('%s' % (subfield(**kwargs)))

        # html.append('</%s>' % self.html_tag)
        return widgets.HTMLString(''.join(html))


class WPPointField(f.TextField):
    attributes = {'class': 'point-widget'}


class WPListField(StaticAttributesMixin, f.TextField):

    def _value(self):

        if self.raw_data:
            return ",".join(self.raw_data)

        return ",".join(self.data) if self.data else ""

    def convert(self, value):

        if not isinstance(value, list):
            return value.split(",") if value else []

        return value

    def process_data(self, value):

        if not isinstance(value, list):
            self.data = value.split(",") if value else []
        else:
            self.data = value

    def process_formdata(self, valuelist):

        if valuelist:
            value = valuelist[0].strip(",")
            self.data = self.convert(value)


class WPTextListField(f.Field):

    widget = TextListWidget()
    option_widget = widgets.TextArea()
    sections = None

    def __init__(self, label=None, validators=None, option_widget=None, sections=None, **kwargs):
        super(WPTextListField, self).__init__(label, validators, **kwargs)

        if option_widget is not None:
            self.option_widget = option_widget

        if sections is not None:
            self.sections = sections

    def __iter__(self):
        opts = dict(
            widget=self.option_widget, _name=self.name, _form=None, _meta=self.meta)
        for i, value in enumerate(self.iter_sections()):
            opt = self._Option(id='%s-%d' % (self.id, i), **opts)
            opt.process(None, value)
            yield opt

    def iter_sections(self):
        for value in self.data:
            print("value:", value)
            yield value

    class _Option(f.Field):

        def _value(self):
            return text_type(self.data)

    def _value(self):

        if self.raw_data:
            return json.dumps(self.raw_data)

        return json.dumps(self.data) if self.data else ""

    def process_data(self, value):

        if not isinstance(value, list) or not value:
            try:
                value = json.loads(value) if value else [""]
                self.data = value if value else [""]
            except Exception:
                self.data = [""]

        elif len(value) == 0:
            self.data = [""]
        else:
            self.data = value

    def process_formdata(self, valuelist):

        if valuelist:
            self.data = [content.strip()
                         for content in valuelist if content.strip()]

    def pre_validate(self, form):
        pass


class WPSelectField(f.SelectField):

    def pre_validate(self, form):
        pass


class WPDecimalField(f.DecimalField):
    """docstring for DecimalField"""

    def __init__(self, label=None, validators=None, places=None, rounding=None, **kwargs):

        if places is None:
            places = 2

        super(WPDecimalField, self).__init__(label, validators, places=places, rounding=rounding, **kwargs)


class ModelConverter(ModelConverter_):

    defaults = {
        BigIntegerField: f.IntegerField,
        BlobField: f.TextAreaField,
        BooleanField: f.BooleanField,
        CharField: f.TextField,
        DateField: WPDateField,
        DateTimeField: WPDateTimeField,
        DecimalField: WPDecimalField,
        DoubleField: f.FloatField,
        FloatField: f.FloatField,
        IntegerField: f.IntegerField,
        PrimaryKeyField: f.HiddenField,
        TextField: f.TextAreaField,
        TimeField: WPTimeField,
        PointField: WPPointField,
        ListField: WPListField,
        TextListField: WPTextListField,
        PasswordField: f.PasswordField,
        JSONTextField: f.TextAreaField,
        JSONField: f.TextAreaField
    }


class NoValidateSelectField(f.SelectField):

    def pre_validate(self, form):
        pass


class NoValidateSelectMultipleField(f.SelectMultipleField):

    """docstring for SelectMultipleField"""

    def pre_validate(self, form):
        pass


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
            raise ValidationError(self.message)


def log_sql(db):
    """Log sql before it gets executed.
    Usage:
        from ext.database import db
        log_sql(db.database)
    """
    import types

    execute_sql = db.execute_sql

    def _execute_sql(self, *args, **kwargs):
        _logger.debug(args)
        _logger.debug(kwargs)
        return execute_sql(*args, **kwargs)

    db.execute_sql = types.MethodType(_execute_sql, db)


class ChoiceField(CharField):

    """
    choice field like Django's
    the choices is ((key, value),)
    """

    def db_value(self, value):
        if value in list(zip(*self.choices))[0]:
            return value
        return self.default

    def python_value(self, value):
        # return dict(self.choices)[value]
        return value


# MultiChoiceField 多项选择字段
MultiChoiceField = ListField
