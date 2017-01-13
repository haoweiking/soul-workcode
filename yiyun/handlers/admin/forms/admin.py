# coding=utf-8

from wtforms import Form, validators, ValidationError
from wtforms import fields as f

from yiyun.helpers import is_mobile
from yiyun.models import Admin, ChinaCity


class CreateAdminForm(Form):
    username = f.StringField("用户名",
                             validators=[
                                 validators.DataRequired(message="不能为空"),
                                 validators.Length(3, 32)
                             ])
    password = f.PasswordField("密码",
                               validators=[
                                   validators.DataRequired(message="不能为空"),
                                   validators.Length(5, 32)
                               ])
    name = f.StringField("名字",
                         validators=[
                             validators.DataRequired(message="不能为空")
                         ])
    mobile = f.StringField("手机",
                           validators=[
                               validators.Optional()
                           ])
    email = f.StringField("电子邮箱",
                          validators=[
                              validators.Optional(),
                              validators.Email(message="格式不正确")
                          ])
    is_super = f.BooleanField("超级管理员")
    roles = f.SelectMultipleField("权限", choices=Admin.ROLES)

    state = f.SelectField("是否启用",
                          choices=[
                              ("1", "启用"),
                              ("0", "禁用"),
                          ])

    manage_provinces = f.SelectMultipleField("管辖省份",
                                             choices=ChinaCity.get_provinces())

    def validate_username(self, field):
        if Admin.select().where(Admin.username == field.data).count() > 0:
            raise ValidationError('用户名已存在')

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')


class EditAdminForm(Form):
    newpassword = f.PasswordField("登录密码",
                                  description="不修改密码请留空",
                                  validators=[
                                      validators.Optional(),
                                      validators.Length(5, 32)
                                  ])

    name = f.StringField("名字",
                         validators=[
                             validators.DataRequired(message="不能为空")
                         ])

    mobile = f.StringField("手机",
                           validators=[
                               validators.Optional()
                           ])

    email = f.StringField("电子邮箱",
                          validators=[
                              validators.Optional(),
                              validators.Email(message="格式不正确")
                          ])

    is_super = f.BooleanField("超级管理员")
    roles = f.SelectMultipleField("权限", choices=Admin.ROLES)

    state = f.SelectField("是否启用",
                          choices=[
                              ("1", "启用"),
                              ("0", "禁用"),
                          ])

    manage_provinces = f.SelectMultipleField("管辖省份",
                                             choices=ChinaCity.get_provinces())

    def validate_mobile(self, field):
        if not is_mobile(field.data):
            raise ValidationError('手机号码格式不正确')
