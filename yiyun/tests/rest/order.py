import json
import unittest
from ..base import AsyncAPITestCase
from yiyun.models import (User, Team, TeamMember, TeamMemberGroup,
                          Sport, Activity,
                          ActivityMember, TeamOrder)
from yiyun.service.order import OrderService


class UserOrderTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [Sport, User, Team, TeamMember, TeamMemberGroup,
                       Activity, ActivityMember, TeamOrder]
    LIST_PATH = "api/2/users/self/orders"
    ORDER_DETAIL = LIST_PATH + "/{order_no}"

    def setUp(self):
        super(UserOrderTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        self.team_owner = User.create(name='test_activity')
        self.team = Team.create(name='club_test_activity',
                                owner_id=self.team_owner.id)
        self.user = self.creator = User.create(name='activity_creator')
        self.activity = Activity.create(team=self.team,
                                        creator=self.creator,
                                        price='10', vip_price='8',
                                        leader=self.creator,
                                        title='just a test',
                                        description='description',
                                        start_time='3000-01-01 00:00:01',
                                        end_time='3000-12-31 23:59:59')

        self.order = OrderService.new_order(10, self.team, self.user,
                                            TeamOrder.OrderType.ACTIVITY,
                                            TeamOrder.OrderPaymentMethod.WXPAY,
                                            self.activity.id,
                                            title="UserOrderTest"
                                            )

        self.activity.add_member(self.user.id,
                                 users_count=1,
                                 price=10,
                                 free_times=0,
                                 total_fee=10,
                                 order_id=self.order.id,
                                 order_no=self.order.order_no,
                                 payment_method=TeamOrder.OrderPaymentMethod.WXPAY,
                                 payment_state=TeamOrder.OrderState.TRADE_BUYER_PAID,
                                 state=TeamMember.TeamMemberState.normal)

    def test_list_all_orders(self):
        self.auth_user = self.user
        response = self.fetch(self.LIST_PATH)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("orders", result, result)
        self.assertNotIn("id", result["orders"][0], result)

    def test_order_detail(self):
        url = self.ORDER_DETAIL.format(order_no=self.order.order_no)

        # 404, not my order
        self.auth_user = self.team_owner
        response = self.fetch(url)
        self.assertEqual(404, response.code, response.body.decode())

        # 200
        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(self.user.id, result["user"]["id"], result)


if __name__ == '__main__':
    unittest.main()
