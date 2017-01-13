from wtforms import validators, ValidationError
from wtforms import fields as f
from wtfpeewee.fields import ModelSelectField, ModelSelectMultipleField

from yiyun.ext.database import WPSelectField, ModelConverter
from yiyun.models import Team, Activity, Sport, ChinaCity
from yiyun.ext.forms import Form, FileField, file_required, file_allowed


class TeamMemberForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
