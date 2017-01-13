from wtforms import validators, ValidationError
from wtforms import fields as f

from yiyun.models import User
from yiyun.helpers import is_mobile

from yiyun.ext.forms import Form, FileField, file_required, file_allowed


class ProfileFrom(Form):
    name = f.StringField("昵称",
                         description="",
                         validators=[
                             validators.DataRequired(message="必填项"),
                             validators.Length(2, 32, message="长度不能少于两位")
                         ])

    gender = f.SelectField("性别", choices=[("m", "男"), ("f", "女")])

    avatarfile = FileField("头像",
                           description="仅支持格式：jpg、png, 不能超过10M",
                           validators=[
                               file_allowed(
                                   ('jpg', "png", "jpeg"), message="格式不支持")
                           ])


class ChangePasswordForm(Form):
    password = f.PasswordField("当前密码",
                               validators=[
                                   validators.DataRequired(message="必填项"),
                                   validators.Length(5, 32, message="长度不能少于5位")
                               ])

    newPassword = f.PasswordField("新密码",
                                  validators=[
                                      validators.DataRequired(message="必填项"),
                                      validators.Length(
                                          5, 32, message="长度不能少于5位")
                                  ])


class ChangeMobileForm(Form):
    password = f.PasswordField("当前登录密码",
                               validators=[
                                   validators.DataRequired(message="必填项")
                               ])

    mobile = f.StringField("手机号码",
                           description="",
                           validators=[
                               validators.DataRequired(message="必填项")
                           ])

    verify_code = f.StringField("验证码",
                                description="",
                                validators=[
                                    validators.DataRequired(message="必填项")
                                ])


class ChangeEmailForm(Form):
    password = f.PasswordField("当前登录密码",
                               validators=[
                                   validators.DataRequired(message="必填项")
                               ])

    new_email = f.StringField("新邮箱",
                              validators=[
                                  validators.DataRequired(message="必填"),
                                  validators.Email(message='必须是邮箱')
                              ])
