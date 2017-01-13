import wtforms
from wtforms import Form, validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import ModelSelectField, ModelSelectMultipleField
from wtfpeewee.orm import model_form

from yiyun.ext.database import WPSelectField
from yiyun.models import Team, Sport, ChinaCity, TeamCertifyApplication
from yiyun.ext.forms import Form, FileField, file_required, file_allowed


class CreateTeamFrom(Form):

    type = f.SelectField("类型",
                         default="1",
                         choices=[
                             ("1", "赛事主办"),
                             ("0", "俱乐部"),
                         ])

    name = f.StringField("名称",
                         description="",
                         validators=[
                             validators.DataRequired(message="必填"),
                             validators.Length(2, 64)
                         ])

    iconfile = FileField("微标",
                         description="仅支持格式：jpg、png, 不能超过10M",
                         validators=[
                             # file_required(message="必填"),
                             file_allowed(("jpg", "png", 'jpeg'),
                                          message="仅支持格式：jpg、png")
                         ])

    sport = ModelSelectMultipleField("运动类型",
                                     model=Sport,
                                     get_label="name"
                                     )

    province = f.SelectField("省份",
                             validators=[
                                 validators.DataRequired(message="必填"),
                             ], choices=ChinaCity.get_provinces())

    city = WPSelectField("城市",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ], choices=[])

    description = f.TextAreaField("介绍",
                                  description="",
                                  validators=[
                                      validators.DataRequired(message="必填"),
                                      validators.Length(5, 2000)
                                  ])

    open_type = f.SelectField("加入验证",
                              choices=[("0", "允许任何人加入"),
                                       ("1", "需要验证"),
                                       # ("2", "交会费加入"),
                                       ("3", "不允许任何人加入")
                                       ])


def convert_text_to_file(form_cls, model_cls, field_names_list):
    """
    将 form 中指定的 field 转化为 file 类型的
    自动生成的时候顺序会发生改变
    """
    for field_name in field_names_list:
        model_field = getattr(model_cls, field_name, None)
        file_field = FileField(model_field.verbose_name,
                               description=model_field.help_text,
                               validators=[
                                   file_allowed(("jpg", "png", 'jpeg'),
                                                message="仅支持格式：jpg、png")
                               ])
        setattr(form_cls, field_name, file_field)

# TODO 验证信息
team_certify_application_exclude = ("id", "created", "team_id", "state", "updated")
team_certify_application_field_args =\
    {"enterprise_name": dict(validators=[validators.DataRequired(message="必填")]),
     "license_number": dict(validators=[validators.DataRequired(message="必填")]),
     "director": dict(validators=[validators.DataRequired(message="必填")]),
     "director_id": dict(validators=[validators.DataRequired(message="必填")]),
     "contact_name": dict(validators=[validators.DataRequired(message="必填")]),
     "contact_phone": dict(validators=[validators.DataRequired(message="必填")])
     }
TeamCertifyApplicationForm = model_form(TeamCertifyApplication,
                                        base_class=Form,
                                        field_args=team_certify_application_field_args,
                                        exclude=team_certify_application_exclude)
field_names_list = ["license_img_key", "director_id_card_front_side_img_key",
                    "director_id_card_back_side_img_key"]
convert_text_to_file(TeamCertifyApplicationForm,
                     TeamCertifyApplication,
                     field_names_list)
