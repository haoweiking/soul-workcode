import json
import datetime
import unittest

from decimal import Decimal
from ..base import AsyncAPITestCase
from yiyun.models import (User, Team, TeamMember, Sport, Activity,
                          ActivityMember, TeamOrder, TeamAccountLog)
from yiyun.tasks.activity import finish_activities, finish_activity


class ActivityTaskTestCase(AsyncAPITestCase):

    REQUIRED_MODELS = [Sport, User, Team, TeamMember, Activity,
                       ActivityMember, TeamOrder, TeamAccountLog]

    def setUp(self):
        super(ActivityTaskTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        self.leader = User.create(name="imleader")
        self.team = Team.create(
            name="test_finish_activity",
            owner_id=self.leader.id
        )
        self.activity = Activity.create(
            team=self.team,
            creator=self.leader,
            leader=self.leader,
            title="test_finish_activity",
            description="test_stoped_activity",
            price=Decimal(15),
            max_members=30,
            start_time=datetime.datetime.now() - datetime.timedelta(hours=2),
            end_time=datetime.datetime.now() - datetime.timedelta(hours=1),
            payment_type=0,
            repeat_type="weekly",
            state=Activity.ActivityState.opening
        )

        self.online_paid_amount = 0

        for i in range(0, 5):
            user = User.create(name="test_%s" % i)
            order = TeamOrder.create(
                team=self.team,
                user=user,
                order_type=0,
                activity_id=self.activity.id,
                title="test_finish",
                order_no=TeamOrder.get_new_order_no(),
                credit_fee=0,
                total_fee=self.activity.price,
                payment_fee=self.activity.price,
                payment_method="wxpay",
                state=TeamOrder.OrderState.TRADE_BUYER_PAID,
                paid=self.activity.start_time,
                created=self.activity.start_time,
                finished=self.activity.start_time
            )
            ActivityMember.create(
                team=self.team,
                activity=self.activity,
                user=user,
                price=self.activity.price,
                users_count=1,
                total_fee=self.activity.price,
                payment_state=order.state,
                payment_method="wxpay",
                order_id=order.id,
                order_no=order.order_no,
                state=ActivityMember.ActivityMemberState.confirmed,
                free_times=0,
            )

            self.online_paid_amount += self.activity.price

        for i in range(0, 3):
            user = User.create(name="test2_%s" % i)
            order = TeamOrder.create(
                team=self.team,
                user=user,
                order_type=0,
                activity_id=self.activity.id,
                title="test_finish",
                order_no=TeamOrder.get_new_order_no(),
                credit_fee=0,
                total_fee=self.activity.price,
                payment_fee=self.activity.price,
                payment_method="wxpay",
                state=TeamOrder.OrderState.WAIT_BUYER_PAY,
                created=self.activity.start_time,
                finished=self.activity.start_time
            )
            ActivityMember.create(
                team=self.team,
                activity=self.activity,
                user=user,
                price=self.activity.price,
                users_count=1,
                total_fee=self.activity.price,
                payment_state=order.state,
                payment_method="wxpay",
                order_id=order.id,
                order_no=order.order_no,
                state=ActivityMember.ActivityMemberState.wait_confirm,
                free_times=0,
            )

    def test_finish_activity(self):
        finish_activity(self.activity.id)

        try:
            finish_activity(self.activity.id)
        except Exception as e:
            pass

        finished_activity = Activity.get(id=self.activity.id)
        rich_team = Team.get(id=self.team.id)

        new_activity = Activity.get(parent_id=self.activity.id)

        self.assertEqual(self.online_paid_amount,
                         finished_activity.online_paid_amount)
        self.assertEqual(finished_activity.state,
                         Activity.ActivityState.finished)
        self.assertEqual(rich_team.credit, self.online_paid_amount)
        self.assertIsInstance(new_activity, Activity)

if __name__ == "__main__":
    unittest.main()
