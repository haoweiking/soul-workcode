import os.path

from wtforms import validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import ModelSelectField

from yiyun.ext.database import WPSelectField
from yiyun.ext.forms import Form


class ApplyCashFrom(Form):

    amount = f.FloatField("提现金额",
                          validators=[
                              validators.DataRequired(message="必填项"),
                              validators.NumberRange(min=1, message="提现金额必须大于1元")
                          ])
