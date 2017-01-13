from yiyun.libs.peewee_serializer import Serializer, SerializerField
from yiyun.models import Team, TeamMember
from .user import UserSimpleSerializer as UserSimpleSerilizer


class SimpleTeamSerializer(Serializer):

    class Meta:
        # only = (Team.id, Team.city, Team.state)
        exclude = (Team.icon_key, )
        extra_attrs = ('icon',)


class MiniTeamSerializer(Serializer):

    class Meta:
        only = (Team.id, Team.name, Team.verified, Team.description,
                Team.members_count, Team.followers_count)
        extra_attrs = ('icon',)


class TeamSerializer(Serializer):

    def __init__(self, instance=None, source=None, **kwargs):
        self.request = kwargs.pop("request", None)
        super(TeamSerializer, self).__init__(instance=instance, source=source)

    owner = UserSimpleSerilizer(source='owner')
    is_member = SerializerField(source='judge_is_member')

    class Meta:
        exclude = (Team.icon_key, )

        extra_attrs = ('icon',)

    def judge_is_member(self):
        if self.request and self.request.current_user:
            current_user = self.request.current_user
            return self.instance.is_member(user_id=current_user.id)
        else:
            return False


class SimpleMemberSerializer(Serializer):

    class Meta:
        only = (TeamMember.id, TeamMember.nick, TeamMember.joined,
                TeamMember.is_vip, TeamMember.activities_count,
                TeamMember.last_update_time)
        exclude = (TeamMember.inviter, TeamMember.role,
                   TeamMember.push_enabled, TeamMember.credit,
                   TeamMember.credit_limit, TeamMember.free_times,
                   TeamMember.total_recharge, TeamMember.created)


class InsecureMemberSerializer(Serializer):
    """
    Insecure Serializer
    包含敏感信息的序列化输出,
    比如会员手机号, 余额等非公开访问的信息
    """

    user = UserSimpleSerilizer(source='user')

    class Meta:
        exclude = (TeamMember.user, TeamMember.created)
