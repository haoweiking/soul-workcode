from wtforms import Form, validators, ValidationError
from wtforms import fields as f
from yiyun.models import ChinaCity
from yiyun.ext.database import WPSelectField

from yiyun.helpers import is_mobile, is_email


class RegisterForm(Form):

    email = f.StringField("邮箱",
                          validators=[
                              validators.DataRequired(message="必填"),
                              validators.Email(message="必须是电子邮箱")
                          ])

    captcha = f.StringField("图形验证码",
                            validators=[
                                validators.DataRequired(message="必填")
                            ])

    name = f.StringField("昵称",
                         validators=[
                             validators.DataRequired(message="必填"),
                             validators.Length(1, 40, message="长度不符合要求")
                         ])

    password = f.PasswordField("登录密码",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   validators.Length(5, 32, message="长度不符合要求"),
                                   validators.EqualTo('confirmed_password',
                                                      message="密码需要和确认密码相同")
                               ])

    province = f.SelectField("省份",
                             validators=[
                                 validators.DataRequired(message="必填"),
                             ], choices=ChinaCity.get_provinces())

    city = WPSelectField("城市",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ], choices=[])

    confirmed_password = f.PasswordField("确认密码",
                                         validators=[
                                             validators.DataRequired(message="必填"),
                                             validators.Length(5, 32,
                                                               message="长度不符合要求")
                                         ])


class LoginForm(Form):

    username = f.StringField("用户名",
                             validators=[
                                 validators.DataRequired(message="必填")
                             ])

    password = f.PasswordField("登录密码",
                               description="",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   validators.Length(5, 32, message="长度不符合要求")
                               ])

    def validate_username(self, field):
        username = field.data
        if not is_mobile(username) and not is_email(username):
            raise ValidationError("用户名必须是邮箱或手机号")


class EmailResetPasswordForm(Form):

    email = f.StringField("注册邮箱",
                          validators=[
                              validators.DataRequired(message="必填"),
                              validators.Email(message="必须是电子邮箱")
                          ])

    verify_code = f.StringField("重置密码验证码",
                                validators=[
                                    validators.DataRequired(message="必填")
                                ])

    new_password = f.PasswordField("新密码",
                                   validators=[
                                       validators.DataRequired(message="必填"),
                                       validators.Length(5, 32, message="长度不符合要求"),
                                       validators.EqualTo("confirmed_password",
                                                          message="密码需要和确认密码相同")
                                   ])

    confirmed_password = f.PasswordField("确认密码",
                                         validators=[
                                             validators.DataRequired(message="必填"),
                                             validators.Length(5, 32,
                                                               message="长度不符合要求")
                                         ])


class MobileResetPasswordForm(Form):

    mobile = f.StringField("手机号码",
                           validators=[
                               validators.DataRequired(message="必填"),
                           ])

    captcha_code = f.StringField("验证码",
                                 validators=[
                                     validators.DataRequired(message="必填")
                                 ])

    verify_code = f.StringField("短信验证码",
                                validators=[
                                    validators.DataRequired(message="必填")
                                ])

    password = f.PasswordField("登录密码",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   validators.Length(5, 32)
                               ])

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')


class LoginVerifyCodeForm(Form):

    mobile = f.StringField("手机号码",
                           validators=[
                               validators.DataRequired(message="必填")
                           ])

    captcha_code = f.StringField("验证码",
                                 validators=[
                                     validators.DataRequired(message="必填")
                                 ])

    verify_code = f.StringField("短信验证码",
                                validators=[
                                    validators.DataRequired(message="必填")
                                ])

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')
