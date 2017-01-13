from voluptuous import Schema, REMOVE_EXTRA, Invalid
from yiyun.models import User
from .base import date_validator


def gender_validator(v):
    choices = [member.value for  member in User.UserGender]
    if v in choices:
        return v
    raise Invalid("不存在的性别选项 {value}".format(value=v))


patch_user = Schema({
    "name": str,
    "signature": str,
    "gender": gender_validator,
    "dob": date_validator(),
}, required=False, extra=REMOVE_EXTRA)
