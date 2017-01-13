from wtforms import validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import (ModelSelectField, ModelSelectMultipleField,
                              WPDateField, WPTimeField)

from yiyun.ext.database import WPSelectField, ModelConverter
from yiyun.models import User, Team, TeamMemberGroup, Activity, Sport, ChinaCity
from yiyun.ext.forms import (Form, FileField, file_required, file_allowed,
                             MultiCheckboxField, LaterThan)


class CreateActivityFrom(Form):

    def __init__(self, *args, **kwargs):
        super(CreateActivityFrom, self).__init__(*args, **kwargs)

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

        leaders = team.get_members(role="leader")
        leaders.insert(0, User.get_or_none(id=team.owner_id))

        if leaders:
            self.leader.choices = [
                (str(user.id), user.name or user.mobile) for user in leaders]

        groups = team.groups
        if groups:
            self.allow_groups.choices = [
                (str(group.id), group.name) for group in groups]

    title = f.StringField("活动标题",
                          description="",
                          validators=[
                              validators.DataRequired(message="必填"),
                              validators.Length(2, 32)
                          ])

    cover = FileField("活动图片",
                      description="仅支持格式：jpg、png, 不能超过2M",
                      validators=[
                          file_allowed(("jpg", "png", "jpeg"),
                                       message="仅支持格式：jpg、png")
                      ])

    sport = ModelSelectField("运动类型",
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

    address = f.StringField("详细地址",
                            description="非场地运动新填写集合地点",
                            validators=[
                                validators.DataRequired(message="必填"),
                            ])

    lat = f.HiddenField("lat")
    lng = f.HiddenField("lng")
    formatted_address = f.HiddenField("address_name")

    start_time = f.DateTimeField("开始时间",
                                 description="首次活动开始时间",
                                 validators=[
                                     validators.DataRequired(message="必填")
                                 ])

    end_time = f.DateTimeField("结束时间",
                               validators=[
                                   validators.DataRequired(message="必填"),
                                   LaterThan("start_time",
                                             message="必须晚于活动开始时间")
                               ])

    repeat_type = f.SelectField("循环活动",
                                description="活动结算后系统自动生成下期活动",
                                choices=[("", "不循环"),
                                         #  ("day", "每天"),
                                         ("week", "每周"),
                                         #  ("month", "每月")
                                         ])

    repeat_end = f.DateTimeField("结束循环",
                                 description="超过此时间活动将不能自动循环",
                                 validators=[
                                     validators.Optional(),
                                     LaterThan("start_time",
                                               message="必须晚于活动开始时间")
                                 ])

    join_end = f.DateTimeField("报名截止时间",
                               description="",
                               validators=[
                                   validators.Optional()
                               ])

    description = f.TextAreaField("活动说明",
                                  description="",
                                  validators=[
                                      validators.DataRequired(message="必填"),
                                      validators.Length(
                                          1, 5000, message="不能超过5000字")
                                  ])

    max_members = f.IntegerField("人数限制",
                                 description="活动限制人数",
                                 default=15,
                                 validators=[
                                     validators.Optional(),
                                     validators.NumberRange(
                                         2, 20000, message="人数限制必须在2到20000人之间")
                                 ])

    allow_agents = f.IntegerField("允许代报人数",
                                  description="代报人数不包含报名人自己",
                                  default=0,
                                  validators=[
                                      validators.Optional(),
                                      validators.NumberRange(
                                          0, 200, message="允许代报人数限制必须在0到200人之间")
                                  ])

    payment_type = f.SelectField("支付方式",
                                 default="",
                                 choices=[("0", "在线支付"), ("1", "线下支付")],
                                 validators=[
                                     validators.DataRequired(message="必填")
                                 ])

    price = f.DecimalField("价格(人/次)", description="")
    # female_price = f.DecimalField("女成员价格")
    vip_price = f.DecimalField("VIP价格(人/次)", description="VIP会员专享价格")

    allow_free_times = f.BooleanField("允许使用次卡")

    visible = f.SelectField("允许报名",
                            default="",
                            choices=[("0", "所有人"), ("1", "仅成员")],
                            validators=[
                                validators.Optional()
                            ])

    allow_groups = f.SelectMultipleField("允许分组",
                                         default="",
                                         description="例如：限制只能高级组会员可以报名，默认不限",
                                         choices=[],
                                         validators=[
                                             validators.Optional()
                                         ])

    leader = f.SelectField("组织者", choices=[])

    need_fields = f.SelectMultipleField("需要填写的报名信息",
                                        description="您希望报名人员填写哪些信息",
                                        default=[
                                            'need_nickname',
                                            'need_gender',
                                            'need_mobile'
                                        ],
                                        choices=[("need_nickname", "昵称"),
                                                 ("need_mobile", "手机"),
                                                 ("need_gender", "性别"),
                                                 ("need_name", "姓名"),
                                                 ("need_identification", "身份证明"),
                                                 ("need_emergency_contact", "紧急联系人")
                                                 ])

    need_ext1_name = f.StringField("信息名称",
                                   description="不需要请留空")
    need_ext1_type = f.SelectField("类型",
                                   choices=(('text', '文本'), ('photo', '照片')))

    need_ext2_name = f.StringField("信息名称")
    need_ext2_type = f.SelectField("类型",
                                   choices=(('text', '文本'), ('photo', '照片')))

    need_ext3_name = f.StringField("信息名称")
    need_ext3_type = f.SelectField("类型",
                                   choices=(('text', '文本'), ('photo', '照片')))
