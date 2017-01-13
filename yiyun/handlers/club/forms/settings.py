import os.path

from wtforms import validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import ModelSelectMultipleField

from yiyun.ext.database import WPSelectField
from yiyun.models import Team, Sport, ChinaCity
from yiyun.ext.forms import Form, FileField, file_required, file_allowed


class TeamBasicFrom(Form):

    name = f.StringField("名称",
                         description="俱乐部或赛事主办机构名称",
                         validators=[
                             validators.DataRequired(message="必填项"),
                             validators.Length(2, 64)
                         ])

    iconfile = FileField("徽标",
                         description="仅支持格式：jpg、png, 不能超过10M",
                         validators=[
                             file_allowed(("jpg", "png", "jpeg"),
                                          message="仅支持格式：jpg、png")
                         ])

    sport = ModelSelectMultipleField("运动类型",
                                     model=Sport,
                                     get_label="name"
                                     )

    province = f.SelectField("省份",
                             validators=[
                                 validators.DataRequired(message="必填项"),
                             ], choices=ChinaCity.get_provinces())

    city = WPSelectField("城市",
                         validators=[
                             validators.DataRequired(message="必填项"),
                         ], choices=[])

    address = f.StringField("联系地址",
                            description="",
                            validators=[
                                validators.Optional(),
                                validators.Length(3, 128)
                            ])

    lat = f.HiddenField("lat")
    lng = f.HiddenField("lng")

    contact_person = f.StringField("联系人",
                                   description="",
                                   validators=[
                                       validators.Optional(),
                                       validators.Length(2, 32)
                                   ])

    contact_phone = f.StringField("联系电话",
                                  description="",
                                  validators=[
                                      validators.Optional(),
                                      validators.Length(3, 32)
                                  ])

    description = f.TextAreaField("介绍",
                                  description="",
                                  validators=[
                                      validators.DataRequired(message="必填"),
                                      validators.Length(5, 2000)
                                  ])


class TeamMemberForm(Form):

    open_type = f.SelectField("加入验证",
                              choices=[("0", "允许任何人加入"),
                                       ("1", "需要验证"),
                                       # ("2", "交会费加入"),
                                       ("3", "不允许任何人加入")
                                       ])


class TeamFinanceForm(Form):

    default_credit_limit = f.DecimalField("默认透支额度")

    cash_type = f.SelectField("提现方式",
                              choices=[
                                  ("alipay", "支付宝"),
                              ])
    cash_account = f.StringField("帐号")
    cash_username = f.StringField("账户姓名")

    recharge_enabled = f.SelectField("开启在线充值",
                                     choices=[("1", "开启"), ("0", "关闭"),
                                              ])


class TeamWeixinForm(Form):

    reply_subscribe = f.TextAreaField("关注自动回复",
                                      description="用户关注后自动回复内容")
    reply_include_url = f.BooleanField("消息结尾添加微门户链接",
                                       description="结尾添加微门户链接用户可以直接点击链接报名活动")
