import random
import time
from datetime import datetime
from decimal import Decimal

from .base import BaseModel

from peewee import (fn, BigIntegerField, CharField, TextField, DateTimeField,
                    ForeignKeyField, IntegerField, BooleanField,
                    FloatField, DecimalField, PrimaryKeyField, DateField,
                    BlobField, DoubleField, TimeField, ImproperlyConfigured,
                    CompositeKey, IntegrityError)

from yiyun.ext.database import (GeoHashField, JSONTextField, ChoiceField,
                                ListField, PointField)

from yiyun.core import current_app as app
from yiyun.models import User


class Order(BaseModel):
    """docstring for Order"""

    user = ForeignKeyField(User)
    order_type = CharField()

    total = DecimalField()


class OrderItem(BaseModel):
    pass


class OrderHistory(BaseModel):
    pass
