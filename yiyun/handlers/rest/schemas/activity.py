import logging
from voluptuous import (Schema, REMOVE_EXTRA, Coerce, Invalid, Required, All,
                        Range, MultipleInvalid, ExclusiveInvalid)

from yiyun.handlers.rest.schemas.base import (datetime_validator,
                                              phone_validator)
from yiyun.models import TeamOrder

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MySchema(Schema):

    def __call__(self, data):
        """Validate data against this schema."""
        try:
            values = self._compiled([], data)
            if hasattr(self, 'after_validate'):
                return self.after_validate(values)
            return values
        except MultipleInvalid:
            raise
        except Invalid as e:
            raise MultipleInvalid([e])

    def after_validate(self, values):
        errors = []
        for key in values.keys():
            method_name = key + '_validator'
            if hasattr(self, method_name):
                try:
                    getattr(self, method_name)(values)
                except Invalid as e:
                    errors.append(ExclusiveInvalid(e.msg, [key]))
        if errors:
            raise MultipleInvalid(errors)
        return values


class ActivityOnlySchema(MySchema):

    def repeat_type_validator(self, values):
        repeat_type = values['repeat_type']
        choices = (
            # ("", "不循环"),
            ("day", "每天"),
            ("week", "每周"),
            ("month", "每月")
        )
        if repeat_type in [value for value, display in choices]:
            if "repeat_end" not in values:
                raise Invalid("需要重复结束日期")
            return repeat_type
        logging.debug("不支持的循环类型: {0}".format(repeat_type))
        raise Invalid("不支持的循环类型")

    def repeat_end_validator(self, values):
        repeat_end = values['repeat_end']
        if repeat_end < values['end_time']:
            raise Invalid("循环结束时间必须大于活动开始时间")


create_activity = ActivityOnlySchema({
    Required("team_id", msg="需要俱乐部 ID"): Coerce(int),
    Required("title", msg="需要活动标题"): str,
    Required('contact_person', msg="需要联系人"): str,
    Required('contact_phone', msg="需要联系人电话"): str,
    Required('description', msg="需要活动描述"): str,
    'country': str,
    'province': str,
    'city': str,
    'address': str,
    'gym_id': Coerce(int),
    'mix_members': Coerce(int),
    'max_members': Coerce(int),
    'public_memebers': Coerce(int),
    'recommend_time': datetime_validator(DATETIME_FORMAT),
    'recommend_region': Coerce(int),
    'allow_free_times': Coerce(int),
    'allow_agents': bool,
    Required('start_time', msg="需要活动开始时间"):
        datetime_validator(DATETIME_FORMAT),
    Required('end_time', msg="需要活动结束时间"):
        datetime_validator(DATETIME_FORMAT),
    Required('join_start', msg="需要报名开始时间"): All(
        Coerce(int, msg="报名开始时间只能是整数"),
        Range(min=1)
    ),
    Required('join_end', msg="需要报名截止时间"): All(
        Coerce(int, msg="结束时间只能是整数"),
        Range(min=0, max=48)
    ),
    "repeat_type": str,
    "repeat_end": datetime_validator(DATETIME_FORMAT),
    "month_day": Coerce(int),
    "week_day": Coerce(int),
    Required("price", msg="需要活动价格"): Coerce(float),
    Required("female_price", msg="女生价格"): Coerce(float),
    Required("vip_price", msg="需要 VIP 价格"): Coerce(float),
    "join_level_discount": bool,
    'need_nickname': bool,
    'need_mobile': bool,
    'need_gender': bool,
    'need_name': bool,
    'need_identification': bool,
    'need_emergency_contact': bool,
    'need_gps': bool,
    'need_ext1_name': str,
    'need_ext1_type': str,
    'need_ext2_name': str,
    'need_ext2_type': str,
    'need_ext3_name': str,
    'need_ext3_type': str,
    'visible': Coerce(int)
    }, extra=REMOVE_EXTRA)


patch_activity = Schema({
    'title': str,
    'contact_person': str,
    'contact_phone': str,
    'description': str,
    'country': str,
    'province': str,
    'city': str,
    'address': str,
    'gym_id': Coerce(int),
    'mix_members': Coerce(int),
    'max_members': Coerce(int),
    'public_memebers': Coerce(int),
    'recommend_time': datetime_validator(DATETIME_FORMAT),
    'recommend_region': Coerce(int),
    'allow_free_times': Coerce(int),
    'allow_agents': bool,
    'join_start': datetime_validator(DATETIME_FORMAT),
    'join_end': datetime_validator(DATETIME_FORMAT),
    'need_nickname': bool,
    'need_mobile': bool,
    'need_gender': bool,
    'need_name': bool,
    'need_identification': bool,
    'need_emergency_contact': bool,
    'need_gps': bool,
    'need_ext1_name': str,
    'need_ext1_type': str,
    'need_ext2_name': str,
    'need_ext2_type': str,
    'need_ext3_name': str,
    'need_ext3_type': str,
    'visible': Coerce(int)
}, extra=REMOVE_EXTRA)


def online_payment_validator(value):
    choice = [member.value for member in list(TeamOrder.OrderPaymentMethod)]
    if value in choice:
        return value
    raise Invalid('不支持的在线支付方式')


join_activity = Schema({
    "payment": online_payment_validator,
    Required("nickname", msg="请填写昵称"): Coerce(str, msg="请填写昵称"),
    Required("users_count", default=1): All(
        Coerce(int, msg="人数必须是整数"),
        Range(min=1, msg="人数必须是大于0的整数")),
    Required("gps_enabled", default=True): bool,
    Required("mobile", default=None): str,
    Required("gender", default=""): str,
    Required("name", default=""): str,
    Required("identification", default=""): str,
    Required("emergency_contact", default=""): str
}, required=True, extra=REMOVE_EXTRA)


pay_activity = Schema({
    "payment": online_payment_validator
}, required=True, extra=REMOVE_EXTRA)


patch_member_profile = Schema({
    "nickname": str,
    "mobile": phone_validator,
    "realname": str,
    "gender": str,
    "gps_enabled": bool,
    "identification": bool,
    "emergency_contact": phone_validator
}, required=False, extra=REMOVE_EXTRA)