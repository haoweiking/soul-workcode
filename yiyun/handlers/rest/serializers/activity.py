from yiyun.libs.peewee_serializer import Serializer
from yiyun.models import Sport, User, Team, Activity, ActivityMember
from .user import UserSimpleSerializer


class OwnerSerializer(Serializer):

    class Meta:
        only = [User.name, User.mobile]


class SportSerializer(Serializer):

    class Meta:
        only = [Sport.name, Sport.id]


class TeamSerializer(Serializer):
    owner = OwnerSerializer()

    class Meta:
        only = [Team.id, Team.name]


class ActivitySerializer(Serializer):
    team = TeamSerializer(source='team')
    leader = UserSimpleSerializer(source="leader")
    creator = UserSimpleSerializer(source='creator')

    class Meta:
        backrefs = True
        only = (Activity.id, Activity.title, Activity.type, Activity.sport,
                Activity.description,
                Activity.comments_count, Activity.recommend_time,
                Activity.recommend_region, Activity.payment_type,

                # 活动联系人信息
                Activity.contact_person, Activity.contact_phone,

                # 场地信息
                Activity.country, Activity.city, Activity.address,
                Activity.lat, Activity.lng, Activity.gym_id,

                # 报名相关信息, 人数/费用/报名时间等..
                Activity.min_members, Activity.max_members,
                Activity.public_memebers, Activity.members_count,
                Activity.allow_groups, Activity.allow_free_times,
                Activity.allow_agents, Activity.cancelled,
                Activity.cancel_reason, Activity.verified,
                Activity.verify_reason, Activity.price, Activity.female_price,
                Activity.vip_price, Activity.join_level_discount,
                Activity.need_nickname, Activity.need_mobile,
                Activity.need_gender, Activity.need_name,
                Activity.need_identification, Activity.need_emergency_contact,
                Activity.need_gps, Activity.need_ext1_name,
                Activity.need_ext1_type, Activity.need_ext2_name,
                Activity.need_ext2_type, Activity.need_ext3_name,
                Activity.need_ext3_type, Activity.visible,
                Activity.refund_type, Activity.created, Activity.updated,
                Activity.state,

                Activity.start_time, Activity.end_time, Activity.join_start,
                Activity.join_end,

                # 活动循环信息
                Activity.repeat_type, Activity.repeat_end, Activity.week_day,
                Activity.month_day
                )

        exclude = (Activity.creator, )


class SecureActivityMemberSerializer(Serializer):

    user = UserSimpleSerializer(source="user")
    inviter = UserSimpleSerializer(source='inviter')

    class Meta:
        only = (ActivityMember.activity, ActivityMember.team_id,
                ActivityMember.nickname, ActivityMember.gender,
                ActivityMember.users_count, ActivityMember.payment_method,
                ActivityMember.state, ActivityMember.payment_state,
                ActivityMember.total_fee, ActivityMember.free_times)
        exclude = (ActivityMember.user,
                   ActivityMember.inviter)


class InsecureActivityMemberSerializer(Serializer):

    user = UserSimpleSerializer(source="user")

    class Meta:
        exclude = (ActivityMember.activity, ActivityMember.user)


class SimpleActivitySerializer(Serializer):

    sport = SportSerializer(source="sport")

    class Meta:
        only = (Activity.id, Activity.title, Activity.max_members,
                Activity.sport, Activity.price, Activity.min_members,
                Activity.public_memebers, Activity.members_count,

                Activity.start_time, Activity.end_time,

                # 场地信息
                Activity.country, Activity.city, Activity.address,
                Activity.lat, Activity.lng, Activity.gym_id,
                )
