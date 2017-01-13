#!/usr/bin/env python
# coding=utf-8

"""
    forms.py
    ~~~~~~~~~~~~~
    wtforms extensions for tornado
"""
import re
import os
from datetime import datetime

from tornado.escape import to_unicode, utf8
from tornado.httputil import HTTPFile

from wtforms.ext.i18n.form import Form as BaseForm
from wtforms.i18n import get_translations
from wtforms import fields, validators, widgets, ext
from wtforms import FileField as _FileField
from wtforms.validators import InputRequired, StopValidation
from wtforms.widgets import HTMLString, html_params

from wtforms.fields import (BooleanField, DecimalField, DateField,
                            DateTimeField, FieldList, FloatField, FormField,
                            HiddenField, IntegerField, PasswordField, RadioField, SelectField,
                            SelectMultipleField, SubmitField, TextField, TextAreaField,
                            StringField, DateTimeField)

from wtforms.validators import (ValidationError, Email, email, EqualTo, equal_to,
                                IPAddress, ip_address, Length, length, NumberRange, number_range,
                                Optional, optional, Required, required, Regexp, regexp,
                                URL, url, AnyOf, any_of, NoneOf, none_of)

from wtforms.widgets import (CheckboxInput, FileInput, HiddenInput,
                             ListWidget, PasswordInput, RadioInput, Select, SubmitInput,
                             TableWidget, TextArea, TextInput)


class TornadoInputWrapper(object):

    def __init__(self, multidict):
        self._wrapped = multidict

    def __iter__(self):
        return iter(self._wrapped)

    def __len__(self):
        return len(self._wrapped)

    def __contains__(self, name):
        return (name in self._wrapped)

    def __getitem__(self, name):
        return self._wrapped[name]

    def __setitem__(self, name, value):
        self._wrapped[name] = value

    def __getattr__(self, name):
        return self.__getitem__(name)

    def to_unicode(self, v):
        if isinstance(v, (bytes, str)):
            return to_unicode(v)

        elif isinstance(v, list):
            return [self.to_unicode(x) for x in v]

        return v

    def getlist(self, name):
        try:
            return [self.to_unicode(v) for v in self._wrapped[name]]
        except KeyError:
            return []


class FormTranslations(object):

    messages = {
        "Not a valid choice": "无效的选择",
        "Not a valid integer value": "请填写整数",
        "Not a valid date value": "日期格式有误",
        "Not a valid time value": "时间格式有误",
        "Field must be between %(min)d and %(max)d characters long.": "长度必须在%(min)d与%(max)d之间"
    }

    def gettext(self, string):
        return self.messages.get(string, string)

    def ngettext(self, singular, plural, n):
        return singular


class Form(BaseForm):
    """
    A Form derivative which uses the locale module from Tornado.
    """

    LANGUAGES = ['zh', 'en']

    def _get_translations(self):
        return FormTranslations()

    def process(self, formdata=None, obj=None, **kwargs):
        if formdata is not None and not hasattr(formdata, 'getlist'):
            formdata = TornadoInputWrapper(formdata)
        super(Form, self).process(formdata, obj, **kwargs)


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class FileField(_FileField):
    """
    Werkzeug-aware subclass of **wtforms.FileField**

    Provides a `has_file()` method to check if its data is a FileStorage
    instance with an actual file.
    """

    def has_file(self):
        '''Return True iff self.data is a FileStorage with file data'''
        if not isinstance(self.data, HTTPFile):
            return False
        # filename == None => the field was present but no file was entered
        # filename == '<fdopen>' is for a werkzeug hack:
        return self.data.filename not in [None, '']


class FileRequired(InputRequired):
    """
    Validates that field has a file.

    :param message: error message

    You can also use the synonym **file_required**.
    """

    def __call__(self, form, field):

        if not field.has_file():
            if self.message is None:
                message = field.gettext('This field is required.')
            else:
                message = self.message
            raise StopValidation(message)

file_required = FileRequired


class FileAllowed(object):
    """
    Validates that the uploaded file is allowed by the given
    Flask-Uploads UploadSet.

    :param upload_set: A list/tuple of extention names or an instance
                       of ``flask.ext.uploads.UploadSet``
    :param message: error message

    You can also use the synonym **file_allowed**.
    """

    def __init__(self, upload_set, message=None):
        self.upload_set = upload_set
        self.message = message

    def __call__(self, form, field):
        if not field.has_file():
            return

        filename = field.data.filename.lower()

        if isinstance(self.upload_set, (tuple, list)):
            if any(filename.endswith('.' + x) for x in self.upload_set):
                return
            message = (
                'File does not end with any of the allowed extentions: {}'
            ).format(self.upload_set)
            raise StopValidation(self.message or message)

        if not self.upload_set.file_allowed(field.data, filename):
            raise StopValidation(self.message or
                                 'File does not have an approved extension')

file_allowed = FileAllowed


class GreaterThan(object):

    """
    Compares the values of two fields.
    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """

    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)
        if field.data <= other.data:
            d = {
                'other_label': hasattr(other, 'label') and other.label.text or self.fieldname,
                'other_name': self.fieldname
            }
            message = self.message
            if message is None:
                message = field.gettext('Field must be greater than %(other_name)s.')

            raise ValidationError(message % d)


class LaterThan(object):

    """
    Compares the values of two fields.
    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """

    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)

        if not isinstance(field.data, datetime) or \
                not isinstance(other.data, datetime):
            return

        if field.data <= other.data:
            d = {
                'other_label': hasattr(other, 'label') and other.label.text or self.fieldname,
                'other_name': self.fieldname
            }
            message = self.message
            if message is None:
                message = field.gettext('Field must be later than %(other_name)s.')

            raise ValidationError(message % d)


class BeforeThan(object):

    """
    Compares the values of two fields.
    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """

    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)

        if not isinstance(field.data, datetime) or \
                not isinstance(other.data, datetime):
            return

        if field.data > other.data:
            d = {
                'other_label': hasattr(other, 'label') and other.label.text or self.fieldname,
                'other_name': self.fieldname
            }
            message = self.message
            if message is None:
                message = field.gettext('Field must be before than %(other_name)s.')

            raise ValidationError(message % d)
