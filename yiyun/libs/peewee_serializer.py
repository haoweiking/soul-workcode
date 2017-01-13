"""
peewee 序列化
like:
https://github.com/coleifer/flask-peewee/blob/master/flask_peewee/serializer.py
"""

import copy
import datetime
from collections import OrderedDict

# from playhouse.shortcuts import model_to_dict
from peewee import *
from peewee import Node


DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
DATETIME_FORMAT = ' '.join([DATE_FORMAT, TIME_FORMAT])


def _clone_set(s):
    if s:
        return set(s)
    return set()


def model_to_dict(model, recurse=True, backrefs=False, only=None,
                  exclude=None, seen=None, extra_attrs=None,
                  fields_from_query=None):
    """
    Convert a model instance (and any related objects) to a dictionary.

    :param bool recurse: Whether foreign-keys should be recursed.
    :param bool backrefs: Whether lists of related objects should be recursed.
    :param only: A list (or set) of field instances indicating which fields
        should be included.
    :param exclude: A list (or set) of field instances that should be
        excluded from the dictionary.
    :param list extra_attrs: Names of model instance attributes or methods
        that should be included.
    :param SelectQuery fields_from_query: Query that was source of model. Take
        fields explicitly selected by the query and serialize them.
    """
    only = _clone_set(only)
    extra_attrs = _clone_set(extra_attrs)

    if fields_from_query is not None:
        for item in fields_from_query._select:
            if isinstance(item, Field):
                only.add(item)
            elif isinstance(item, Node) and item._alias:
                extra_attrs.add(item._alias)

    data = {}
    exclude = _clone_set(exclude)
    seen = _clone_set(seen)
    exclude |= seen
    model_class = type(model)

    for field in model._meta.sorted_fields:
        if field in exclude or (only and (field not in only)):
            continue

        field_data = model._data.get(field.name)
        if isinstance(field, ForeignKeyField) and recurse:
            if field_data:
                seen.add(field)
                rel_obj = getattr(model, field.name)
                field_data = model_to_dict(
                    rel_obj,
                    recurse=recurse,
                    backrefs=backrefs,
                    only=only,
                    exclude=exclude,
                    seen=seen)
            else:
                field_data = {}

        data[field.name] = field_data

    if extra_attrs:
        for attr_name in extra_attrs:
            attr = getattr(model, attr_name)
            if callable(attr):
                data[attr_name] = attr()
            else:
                data[attr_name] = attr

    if backrefs:
        for related_name, foreign_key in model._meta.reverse_rel.items():
            descriptor = getattr(model_class, related_name)
            if descriptor in exclude or foreign_key in exclude:
                continue
            if only and descriptor not in only and foreign_key not in only:
                continue

            accum = []
            exclude.add(foreign_key)
            related_query = getattr(
                model,
                related_name + '_prefetch',
                getattr(model, related_name))

            for rel_obj in related_query:
                accum.append(model_to_dict(
                    rel_obj,
                    recurse=recurse,
                    backrefs=backrefs,
                    only=only,
                    exclude=exclude))

            data[related_name] = accum

    return data


class SerializerField(object):
    """
    >>> class UserSerializer(Serializer):
    >>>     tweets_count = SerializerField(source='get_tweets_count')
    >>>     def get_tweets_count(self):
    >>>         return 1000
    """

    def __init__(self, source):
        self.source = source


class SerializerMetaClass(type):

    default_options = {
        'recurse': True,
        'backrefs': False,
        'only': None,
        'exclude ': None,
        'extra_attrs': None
    }
    all_union = ('only', 'exclude', 'extra_attrs')

    def __new__(mcs, name, bases, attrs):
        if not bases:
            return super(SerializerMetaClass, mcs).__new__(mcs, name, bases,
                                                           attrs)

        attrs['_declared_fields'] = mcs._get_declared_fields(bases, attrs)
        attrs['_meta'] = mcs._get_meta_options(bases, attrs)

        return super(SerializerMetaClass, mcs).__new__(mcs, name, bases, attrs)

    @classmethod
    def _get_meta_options(mcs, bases, attrs):
        meta_options = copy.copy(mcs.default_options)
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        for b in bases:
            if not hasattr(b, 'Meta'):
                continue

            # 父类的 Meta 属性可能会被覆盖
            base_meta = getattr(b, '_meta')
            for k, v in base_meta.items():
                if k in mcs.all_union:
                    if meta_options[k]:
                        meta_options[k].append(v)
                    else:
                        meta_options[k] = v
        return meta_options

    @classmethod
    def _get_declared_fields(mcs, bases, attrs: dict):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in
                  list(attrs.items()) if isinstance(obj, BaseSerializer) or
                  isinstance(obj, SerializerField)]

        # 如果是继承自其它 Serializer, 添加父类的 fields
        for base in bases:
            if hasattr(base, '_declared_fields'):
                fields = list(base._declared_fields.items()) + fields
        return dict(fields)


class BaseSerializer(object):

    def __init__(self, instance=None, source=None, **kwargs):
        self.instance = instance
        self.source = source
        self.kwargs = kwargs

    def __call__(self, instance):
        self.instance = instance
        return self

    def convert_value(self, value):
        if isinstance(value, datetime.datetime):
            return value.strftime(DATETIME_FORMAT)
        elif isinstance(value, datetime.date):
            return value.strftime(DATE_FORMAT)
        elif isinstance(value, datetime.time):
            return value.strftime(TIME_FORMAT)
        elif isinstance(value, Model):
            return value.get_id()
        else:
            return value

    def clean_data(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                self.clean_data(value)
            elif isinstance(value, (list, tuple)):
                print(value, 'list or tuple')
                data[key] = [self.clean_data(v) for v in value
                             if isinstance(v, dict)]
            else:
                data[key] = self.convert_value(value)
        return data

    def serialize_object(self, obj, fields=None, exclude=None):
        data = model_to_dict(obj, only=fields, exclude=exclude)
        return self.clean_data(data)

    @property
    def data(self):
        raise NotImplementedError()


class Serializer(BaseSerializer, metaclass=SerializerMetaClass):
    """
    peewee.Model serializer and deserializer
    Normal usage:
    First, define two Model `User` and `Tweet`
    >>> class User(Model):
    >>>     name = CharField(verbose_name='User name')
    >>>
    >>>
    >>> class Tweet(Model):
    >>>     user = ForeignKeyField(User, related_name='tweets')
    >>>     content = CharField(verbose_name='content')
    >>>     created = DateTimeField(default=datetime.datetime.now)
    >>>
    >>>
    >>> class UserSerializer(Serializer):
    >>>     class Meta:
    >>>         only = (User.id, User.name)
    >>>
    >>> user = User.create(name="joe")
    >>> data = UserSerializer(instance=user).data
    >>> print(data)
    >>> {"id": 1, "name": "joe"}

    Nested Serializer:
    >>> class TweetSerializer(Serializer):
    >>>     user = UserSerializer(source='user')
    >>>     class Meta:
    >>>         only = (Tweet.id, Tweet.content)
    >>>         exclude = (Tweet.user,)
    >>>
    >>> tweet = Tweet.create(user=user, content="first tweet")
    >>> print(TweetSerializer(instance=tweet).data)
    >>> {"id": 1, "content": "first tweet", "user": {"id": 1, "name": "joe"}}
    """

    @property
    def data(self):
        data = model_to_dict(self.instance,
                             recurse=self._meta.get('recurse'),
                             only=self._meta.get('only'),
                             exclude=self._meta.get('exclude'),
                             extra_attrs=self._meta.get('extra_attrs'),
                             backrefs=self._meta.get('backrefs'))

        nested_serializes = self._declared_fields
        for field_name, serializer in nested_serializes.items():
            if isinstance(serializer, SerializerField):
                data[field_name] = getattr(self, serializer.source)()
            else:
                source = getattr(self.instance,
                                 serializer.source or field_name)
                if callable(source):
                    data[field_name] = serializer(source()).data
                elif source:
                    data[field_name] = serializer(source).data
                else:
                    # nest serializer 时 如果对应 source 为空返回空的 dict
                    data[field_name] = {}
            # data[field_name] = serializer(
            #     getattr(self.instance, serializer.source or field_name)
            # ).data
        # return self.clean_data(data)
        return data
