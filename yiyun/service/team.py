from peewee import SelectQuery
from .base import ServiceException, BaseService
from yiyun.models import (BaseModel, User, Team, TeamMember, TeamFollower,
                          TeamMemberAccountLog, TeamOrder, TeamMemberGroup)


class TeamService(BaseService):

    @classmethod
    def follow(cls, user_id, team: Team):
        if team.get_follower(user_id=user_id):
            raise ServiceException("已关注俱乐部, 无须重复关注")

        with cls.database.transaction():
            team.add_follower(user_id=user_id)

    @classmethod
    def followers(cls, team: Team) -> SelectQuery:
        """获取俱乐部的粉丝"""
        return TeamFollower.select().where(TeamFollower.team_id == team.id)


class TeamMemberService(object):

    @classmethod
    def new_order(cls, team, activity_id, user, order_type,
                  payment_method, total_fee, payment_fee, title):
        """
        Args:
            total_fee: 订单金额
            payment_fee: 实付金额
            team:
            user:
            order_type: TeamOrder.Order_TYPES 订单类型 参加活动/消费
            payment_method: 支付方式
            activity_id:
            batch_id:
        """
        order = TeamOrder.create(order_no=TeamOrder.get_new_order_no(),
                                 team=team,
                                 user=user,
                                 title=title,
                                 order_type=order_type,
                                 payment_fee=payment_fee,
                                 payment_method=payment_method,
                                 total_fee=total_fee,
                                 activity_id=activity_id,
                                 state=TeamOrder.OrderState.WAIT_BUYER_PAY
                                 )
        return order

    @classmethod
    def recharge(cls, amount, member, payment, operator):
        """
        会员充值
        Args:
            amount: 充值金额
            member: 充值会员
            payment: 支付方式, 'wxpay', 'alipay', 'cash'
            operator: 操作者

        Returns:

        """
        order_type = 1

        with BaseModel._meta.database.atomic() as txn:
            order = TeamOrder.create(order_no=TeamOrder.get_new_order_no(),
                                     team=member.team,
                                     user=member.user,
                                     order_type=order_type,
                                     payment_method=payment,
                                     )


class TeamMemberGroupService(BaseService):

    @classmethod
    def add_member(cls, group: TeamMemberGroup, member: TeamMember):
        """向 Group 中添加成员 """

        with cls.database.atomic():

            # 更新分组的 members_count
            TeamMemberGroup\
                .update(members_count=TeamMemberGroup.members_count + 1)\
                .where(TeamMemberGroup.id == group.id) \
                .execute()

            # 修改会员的 group_name
            TeamMember.update(group_name=group.name) \
                .where(TeamMember.id == member.id)\
                .execute()

    @classmethod
    def remove_member(cls, group: TeamMemberGroup, member: TeamMember):
        """
        从分组中移除成员
        """

        with cls.database.atomic():

            # 更新分组的 members_count
            TeamMemberGroup \
                .update(members_count=TeamMemberGroup.members_count - 1) \
                .where(TeamMemberGroup.id == group.id) \
                .execute()

            # 修改会员的 group_name
            TeamMember.update(group_name=TeamMember.group_name.default) \
                .where(TeamMember.id == member.id) \
                .execute()
