import pickle
import json
from datetime import datetime

from .base import BaseModel
from peewee import CharField, IntegerField, BooleanField, DateTimeField

from yiyun.core import current_app as app
from yiyun.ext.cache import cached_property
from yiyun.resources.china_cities import china_cities


class Client(BaseModel):

    """docstring for Client"""

    name = CharField(default="")
    device_type = CharField(default="ios",
                            max_length=16,
                            choices=[('ios', 'iOS'),
                                     ('android', 'Android'),
                                     ('web', '网站')])

    key = CharField(max_length=32, index=True)
    secret = CharField(max_length=128)

    verify_sign = BooleanField(default=True)
    created = DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'client'

    @classmethod
    def get_client(cls, key, cache=True):

        client = app.redis.get("apiKey:%s" % key) if cache else None
        if not client:
            client = cls.get_or_none(key=key)
            if client:

                if cache:
                    app.redis.set("apiKey:%s" % key, client.to_json())
                    app.redis.expire("apiKey:%s" % key, 3600 * 24 * 7)

                client = client.info
        else:
            client = json.loads(client)

        return client


class Sport(BaseModel):

    name = CharField(unique=True, max_length=20)
    description = CharField(default="", max_length=200)
    is_fight = BooleanField(default=False, verbose_name="是否为对战类型")
    unit = CharField(default="", verbose_name="成绩单位")
    sort = IntegerField(default=0, index=True)

    class Meta:
        db_table = 'sports'
        order_by = ('sort', 'name')

    def __str__(self):
        return self.name

    @classmethod
    def all(cls):
        sports = app.redis.get("yy:sports")

        if not sports:
            c = cls.select().order_by(cls.sort.desc())

            sports = []
            for sport in c:
                sports.append(sport)

            app.redis.set("yy:sports",
                          pickle.dumps(sports, pickle.HIGHEST_PROTOCOL))

        else:
            sports = pickle.loads(sports)

        return sports

    @classmethod
    def get_names(cls, ids):
        sports = cls.select().where(cls.id << ids)
        names = []
        for sport in sports:
            names.append(sport.name)

        return names

    # @classmethod
    # def get(cls, *args, **kwargs):
    #     sport = cls.get_or_none(*args, **kwargs)
    #     return sport


class ChinaCity(object):

    @classmethod
    def get_provinces(cls):
        provinces = [(p['name'], p['name']) for p in china_cities]
        return sorted(provinces, key=lambda p: p[0].encode("GB18030"))

    @classmethod
    def get_cities(cls, province=None):
        cities = {}
        for pv in china_cities:
            cities[pv['name']] = [c['name'] for c in pv['children']]

        if province:
            return [(c, c) for c in cities[province]]

        return cities
