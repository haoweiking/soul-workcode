from yiyun.libs.peewee_serializer import Serializer
from yiyun.models import TeamOrder
from .user import UserSimpleSerializer
from .team import SimpleTeamSerializer
from .activity import SimpleActivitySerializer


class SecureOrderSerializer(Serializer):

    user = UserSimpleSerializer(source='user')
    team = SimpleTeamSerializer(source='team')
    activity = SimpleActivitySerializer(source='activity')

    class Meta:
        exclude = (TeamOrder.id, TeamOrder.user, TeamOrder.team,
                   TeamOrder.payment_data, TeamOrder.gateway_account,
                   TeamOrder.gateway_trade_no,)


class OrderSimpleSerializer(Serializer):

    class Meta:
        exclude = (TeamOrder.id, TeamOrder.user, TeamOrder.team,
                   TeamOrder.payment_data, TeamOrder.gateway_account,
                   TeamOrder.gateway_trade_no,)
