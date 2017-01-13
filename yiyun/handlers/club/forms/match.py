from wtforms import validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import (ModelSelectField, ModelSelectMultipleField,
                              WPDateField, WPTimeField)
from wtfpeewee.orm import model_form

from yiyun.ext.database import WPSelectField, ModelConverter
from yiyun.models import User, Team, TeamMemberGroup, Activity, Sport, \
    ChinaCity, MatchStatus
from yiyun.ext.forms import (Form, FileField, file_required, file_allowed,
                             MultiCheckboxField, LaterThan, BeforeThan)


class CreateMatchFrom(Form):

    def __init__(self, *args, **kwargs):
        super(CreateMatchFrom, self).__init__(*args, **kwargs)

        obj = kwargs.get("obj", None)
        team = kwargs.get("team", None)

        if not isinstance(team, Team):
            raise AssertionError("must a team")

        if obj and obj.province:
            province = obj.province

        else:
            province = self.province.choices[0][0]

        if province:
            self.city.choices = ChinaCity.get_cities(province)

    title = f.StringField("比赛名称",
                          description="",
                          validators=[
                              validators.DataRequired(message="必填"),
                              validators.Length(1, 200, message="不能超过200字")
                          ])

    coverfile = FileField("封面",
                          description="建议尺寸：1045x464，仅支持格式：jpg、png, 不能超过10M",
                          validators=[
                              file_required(message="必填"),
                              file_allowed(("jpg", "png", "jpeg"),
                                           message="仅支持格式：jpg、png")
                          ])

    sport_id = ModelSelectField("运动类型",
                                model=Sport,
                                get_label="name"
                                )

    type = f.SelectField("比赛类型",
                         description="对战型如：足球、蓝球，非对战型：跑步、自行车",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ], choices=(('0', "对战型"), ('1', "非对战型")))

    province = f.SelectField("省份",
                             validators=[
                                 validators.DataRequired(message="必填"),
                             ], choices=ChinaCity.get_provinces())

    city = WPSelectField("城市",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ], choices=[])

    address = f.StringField("详细地址",
                            description="非场地运动新填写集合地点",
                            validators=[
                                validators.DataRequired(message="必填"),
                            ])

    lat = f.HiddenField("lat")
    lng = f.HiddenField("lng")
    formatted_address = f.HiddenField("address_name")

    start_time = f.DateTimeField("开始时间",
                                 description="赛事开始时间",
                                 validators=[
                                     validators.DataRequired(message="必填")
                                 ])

    end_time = f.DateTimeField("结束时间",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   LaterThan("start_time",
                                             message="必须晚于开始时间")
                               ])

    join_start = f.DateTimeField("报名开始时间",
                                 description="限时开始报名，不填赛事上线即可报名",
                                 validators=[
                                     validators.Optional()
                                 ])

    join_end = f.DateTimeField("报名截止时间",
                               description="不填则开始前均可报名",
                               validators=[
                                   validators.Optional(),
                                   BeforeThan("start_time",
                                              message="必须早于开始时间"),
                                   LaterThan("join_start",
                                             message="必须晚于报名开始时间")
                               ])

    contact_person = f.StringField("联系人",
                                   description="",
                                   validators=[
                                       validators.DataRequired(message="必填"),
                                       validators.Length(1, 200,
                                                         message="不能超过200字")
                                   ])

    contact_phone = f.StringField("联系电话",
                                  description="",
                                  validators=[
                                      validators.DataRequired(message="必填"),
                                      validators.Length(1, 200,
                                                        message="不能超过200字")
                                  ])

    description = f.TextAreaField("简介",
                                  description="",
                                  validators=[
                                      validators.DataRequired(message="必填")
                                  ])

    rules = f.TextAreaField("规程",
                            description="",
                            validators=[
                                validators.DataRequired(message="必填")
                            ])

    reward = f.StringField("奖励",
                           description="奖励说明，如：冠军1000元，亚军500元",
                           validators=[
                               validators.Optional(),
                               validators.Length(0, 200,
                                                 message="不能超过200字")
                           ])

    join_type = f.SelectField("报名类型",
                              validators=[
                                  validators.DataRequired(message="必填"),
                              ], choices=(('0', "个人"), ('1', "团队")))

    refund_type = f.SelectField("退款策略",
                                validators=[
                                    validators.DataRequired(message="必填"),
                                ], choices=(('0', "开始前可以退款"),
                                            ('1', "报名截止前可退"),
                                            ('2', "不能退款")))

    max_members = f.IntegerField("人数或团队限制",
                                 description="比赛人数或团队限制，报满则无法继续报名",
                                 default=15,
                                 validators=[
                                     validators.Optional(),
                                     validators.NumberRange(0, 20000,
                                                            message="人数限制必须在2到20000人之间")
                                 ])

    price = f.DecimalField("报名费(元)",
                           description="设置分组后将以分组报名费为准",
                           validators=[
                               validators.Optional()
                           ])

    group_type = f.SelectField("分组模式",
                               validators=[
                                   validators.DataRequired(message="必填"),
                               ], choices=(('0', "非分组比赛"),
                                           ('1', "分组比赛")))

    groups = f.StringField("分组",
                           validators=[
                               validators.Optional()
                           ])


class EditMatchFrom(CreateMatchFrom):

    coverfile = FileField("封面",
                          description="建议尺寸：1045x464，仅支持格式：jpg、png, 不能超过10M",
                          validators=[
                              file_allowed(("jpg", "png", "jpeg"),
                                           message="仅支持格式：jpg、png")
                          ])


class CreateRoundForm(Form):
    name = f.StringField("名称",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ])

    address = f.StringField("地址",
                            validators=[
                                validators.Optional(),
                            ])

    start_time = f.DateTimeField("开始时间",
                                 validators=[
                                     validators.Optional()
                                 ])

    end_time = f.DateTimeField("结束时间",
                               validators=[
                                   validators.Optional(),
                                   LaterThan("start_time",
                                             message="必须晚于开始时间")
                               ])

    description = f.TextAreaField("描述")


class EditRoundForm(Form):
    name = f.StringField("名称",
                         validators=[
                             validators.DataRequired(message="必填"),
                         ])

    address = f.StringField("地址",
                            validators=[
                                validators.Optional(),
                            ])

    start_time = f.DateTimeField("开始时间",
                                 validators=[
                                     validators.Optional()
                                 ])

    end_time = f.DateTimeField("结束时间",
                               validators=[
                                   validators.Optional(),
                                   LaterThan("start_time",
                                             message="必须晚于开始时间")
                               ])
    description = f.TextAreaField("描述")


class CreateCoverForm(Form):

    position = f.SelectField("显示位置",
                             validators=[
                                 validators.DataRequired(message="必填"),
                             ], choices=(('description', "赛事详情"),
                                         ('rules', '赛事规程'),
                                         ('rounds', '赛事赛程')
                                         ))

    coverfile = FileField("海报",
                          description="建议尺寸：1125x500, 支持格式：jpg、png, 不能超过20M",
                          validators=[
                              file_required(message="必填"),
                              file_allowed(("jpg", "png", "jpeg"),
                                           message="仅支持格式：jpg、png")
                          ])


match_status_exclude = ("id", "match_id", "photos", "comments_count", "created", "is_notice",
                        "like_count")
match_status_field_args = {"content": dict(label="内容")}
MatchStatusForm = model_form(MatchStatus, base_class=Form, field_args=match_status_field_args,
                             exclude=match_status_exclude)
