from yiyun.libs.peewee_serializer import Serializer
from yiyun.models import User


class UserSimpleSerializer(Serializer):

    class Meta:
        only = (User.id, User.name, User.signature, User.mobile, User.gender,
                User.dob, User.created)
        exclude = (User.password, User.avatar_key, User.pay_openid,
                   User.reg_device_id, User.reg_device_type,)
        extra_attrs = ('avatar',)


class UserInsecureSerializer(Serializer):

    class Meta:
        exclude = (User.password, User.avatar_key, User.pay_openid,
                   User.reg_device_id, User.reg_device_type,)
        extra_attrs = ('avatar', )
