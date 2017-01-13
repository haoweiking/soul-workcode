from wtforms import Form, validators, ValidationError
from wtforms import fields as f

from yiyun.models import User
from yiyun.helpers import is_mobile


class RegisterFrom(Form):

    mobile = f.StringField("手机号码",
                           description="",
                           validators=[
                               validators.DataRequired(message="必填")
                           ])

    verify_code = f.StringField("验证码",
                                description="",
                                validators=[
                                    validators.DataRequired(message="必填")
                                ])

    name = f.StringField("姓名",
                         description="",
                         validators=[
                             validators.DataRequired(message="必填"),
                             validators.Length(1, 32)
                         ])

    password = f.PasswordField("登录密码",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   validators.Length(5, 32)
                               ])

    confirmPassword = f.PasswordField("确认密码",
                                      validators=[
                                          validators.DataRequired(message="必填"),
                                          validators.Length(5, 32)
                                      ])

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')

        if User.select().where(User.mobile == field.data).exists():
            raise ValidationError('手机号码已存在')


class LoginFrom(Form):

    username = f.StringField("用户名",
                           description="",
                           validators=[
                               validators.DataRequired(message="必填")
                           ])

    password = f.PasswordField("登录密码",
                               description="",
                               validators=[
                                   validators.DataRequired(message="必填")
                               ])

class RestPasswordFrom(Form):

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

    password = f.PasswordField("登录密码",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   validators.Length(5, 32)
                               ])

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')


class LoginVerifyCodeFrom(Form):

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
