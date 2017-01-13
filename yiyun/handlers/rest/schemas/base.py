import datetime
from voluptuous import Invalid
from yiyun.helpers import is_mobile


def datetime_validator(fmt='%Y-%m-%d %H:%M:%S'):
    return lambda v: datetime.datetime.strptime(v, fmt)


def date_validator(fmt="%Y-%m-%d"):
    return lambda v: datetime.datetime.strptime(v, fmt)


def phone_validator(value):
    if is_mobile(value):
        return value
    raise Invalid("手机号码格式错误")


def email_validator(email):
    if "@" not in email:
        raise Invalid("电子邮箱格式不正确")
    return email
