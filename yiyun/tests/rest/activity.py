import json
import datetime
import unittest
from ..base import AsyncAPITestCase
from yiyun.models import (User, Team, TeamMember, Sport, Activity,
                          ActivityMember, TeamOrder)
from yiyun.service.order import OrderService
from yiyun.service.team import TeamMemberService


class ActivityTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, Activity,
                       ActivityMember, TeamOrder]
    MODEL_PATH = 'api/2/activities'
    OBJECT_PATH = 'api/2/activities/{activity_id}'
    JOIN_ACTIVITY = OBJECT_PATH + '/join'

    def setUp(self):
        super(ActivityTestCase, self).setUp()
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
                                        end_time='3000-12-31 23:59:59',
                                        max_members=10)

    def test_create_activity_no_repeat(self):
        url = self.MODEL_PATH
        body = {
            "team_id": self.team.id,
            "title": "activity title",
            "description": "description",
            "contact_person": "contact person",
            "contact_phone": "contact phone",
            "start_time": "3000-01-01 00:00:01",
            "end_time": "4000-01-01 23:59:59",
            "join_start": "2999-12-30 00:00:01",
            "join_end": "4000-01-01 22:59:59",
            "price": 0.01,
            "female_price": 0.01,
            "vip_price": 0.01,
            "city": "成都",
            "address": "天府三街",
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(self.team.id, result["team"]["id"])
        self.assertEqual(self.team_owner.id, result["creator"]["id"], result)

        body.pop("team_id")
        for k, v in body.items():
            _value = result[k]
            if isinstance(_value, datetime.datetime):
                _value = _value.strftime("%Y-%m-%d %H:%M:%S")
            self.assertEqual(v, _value, k)

    def test_create_activity_day_repeat(self):
        url = self.MODEL_PATH
        body = {
            "team_id": self.team.id,
            "title": "activity title",
            "description": "description",
            "contact_person": "contact person",
            "contact_phone": "contact phone",
            "start_time": "3000-01-01 00:00:01",
            "end_time": "4000-01-01 23:59:59",
            "join_start": "2999-12-30 00:00:01",
            "join_end": "4000-01-01 22:59:59",
            "price": 0.01,
            "female_price": 0.01,
            "vip_price": 0.01,
            "city": "成都",
            "address": "天府三街",
            "repeat_type": "day",
            "repeat_end": "4000-01-01 23:59:59"
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(self.team.id, result["team"]["id"])
        self.assertEqual(self.team_owner.id, result["creator"]["id"], result)

        body.pop("team_id")
        for k, v in body.items():
            _value = result[k]
            if isinstance(_value, datetime.datetime):
                _value = _value.strftime("%Y-%m-%d %H:%M:%S")
            self.assertEqual(v, _value, k)

    def test_create_activity_weekly_repeat(self):
        url = self.MODEL_PATH
        body = {
            "team_id": self.team.id,
            "title": "activity title",
            "description": "description",
            "contact_person": "contact person",
            "contact_phone": "contact phone",
            "start_time": "3000-01-01 00:00:01",
            "end_time": "4000-01-01 23:59:59",
            "join_start": "2999-12-30 00:00:01",
            "join_end": "4000-01-01 22:59:59",
            "price": 0.01,
            "female_price": 0.01,
            "vip_price": 0.01,
            "city": "成都",
            "address": "天府三街",
            "repeat_type": "week",
            "repeat_end": "4000-01-01 23:59:59"
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="POST",
                              body=json.dumps(body),
                              headers={
                                  "Content-Type": "application/json"
                              })

        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(self.team.id, result["team"]["id"])
        self.assertEqual(self.team_owner.id, result["creator"]["id"], result)

        body.pop("team_id")
        for k, v in body.items():
            _value = result[k]
            if isinstance(_value, datetime.datetime):
                _value = _value.strftime("%Y-%m-%d %H:%M:%S")
            self.assertEqual(v, _value, k)

        expect_week_day = 1 + datetime.datetime\
            .strptime("3000-01-01 00:00:01",  "%Y-%m-%d %H:%M:%S")\
            .weekday()
        self.assertEqual(expect_week_day, result["week_day"],
                         result["week_day"])

    def test_create_activity_monthly_repeat(self):
        url = self.MODEL_PATH
        body = {
            "team_id": self.team.id,
            "title": "activity title",
            "description": "description",
            "contact_person": "contact person",
            "contact_phone": "contact phone",
            "start_time": "3000-01-01 00:00:01",
            "end_time": "4000-01-01 23:59:59",
            "join_start": "2999-12-30 00:00:01",
            "join_end": "4000-01-01 22:59:59",
            "price": 0.01,
            "female_price": 0.01,
            "vip_price": 0.01,
            "city": "成都",
            "address": "天府三街",
            "repeat_type": "month",
            "repeat_end": "4000-01-01 23:59:59"
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="POST",
                              body=json.dumps(body),
                              headers={
                                  "Content-Type": "application/json"
                              })
        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(self.team.id, result["team"]["id"])
        self.assertEqual(self.team_owner.id, result["creator"]["id"], result)

        body.pop("team_id")
        for k, v in body.items():
            _value = result[k]
            if isinstance(_value, datetime.datetime):
                _value = _value.strftime("%Y-%m-%d %H:%M:%S")
            self.assertEqual(v, _value, k)

        expect_month_day = datetime.datetime \
            .strptime("3000-01-01 00:00:01", "%Y-%m-%d %H:%M:%S") \
            .day
        self.assertEqual(expect_month_day, result["month_day"],
                         result["month_day"])

    def test_list_all(self):
        response = self.fetch(self.MODEL_PATH)
        self.assertEqual(200, response.code, response.body)

    def test_activity_object(self):
        url = self.OBJECT_PATH.format(activity_id=self.activity.id)
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body)
        # result = json.loads(response.body.decode())
        # team = {
        #     'id': self.team.id,
        #     'name': self.team.name,
        #     'owner': {
        #         'name': self.team_owner.name,
        #         'mobile': self.team_owner.mobile
        #     }
        # }
        # creator = {
        #     'name': self.creator.name,
        #     'mobile': self.creator.mobile
        # }
        # batches = [{'id': self.batch.id, 'start_time': '3000-01-01 00:00:01'}]
        # expect = {
        #     'id': self.activity.id,
        #     'title': 'just a test',
        #     'team': team,
        #     'creator': creator,
        #     'batches': batches
        # }
        # self.assertDictEqual(expect, result, result)

    def test_path_object(self):
        body = {
            'title': 'new title',
            'need_name': True
        }
        url = self.OBJECT_PATH.format(activity_id=self.activity.id)

        self.auth_user = self.team_owner
        response = self.fetch(url, method='PATCH', body=json.dumps(body))
        self.assertEqual(403, response.code, response.body)

        self.auth_user = self.creator
        response = self.fetch(url, method='PATCH', body=json.dumps(body))
        self.assertEqual(200, response.code, response.body)

        updated = Activity.get(id=self.activity.id)
        self.assertEqual(updated.title, 'new title')
        self.assertTrue(updated.need_name is True)


class TestJoinActivity(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, Activity,
                       ActivityMember, TeamOrder]
    OBJECT_PATH = 'api/2/activities/{activity_id}'
    JOIN_ACTIVITY = OBJECT_PATH + '/join'
    ACTIVITY_MEMBERS = OBJECT_PATH + '/members'
    MEMBER_DETAIL = ACTIVITY_MEMBERS + '/{member_id}'

    def setUp(self):
        super(TestJoinActivity, self).setUp()
        self.initial_data()

    def initial_data(self):
        self.team_owner = User.create(name='test_activity1')
        self.team = Team.create(name='club_test_activity1',
                                owner_id=self.team_owner.id)
        self.user = self.creator = User.create(name='activity_creator')
        self.activity = Activity.create(team=self.team, creator=self.creator,
                                        price='10', vip_price='8',
                                        leader=self.creator,
                                        title='just a test',
                                        description='description',
                                        join_end="4000-01-01 22:59:59",
                                        start_time='3000-01-01 00:00:01',
                                        end_time='3000-12-31 23:59:59',
                                        max_members=100)

        self.order = OrderService.new_order(10, self.team, self.user,
                                            TeamOrder.OrderType.ACTIVITY,
                                            TeamOrder.OrderPaymentMethod.WXPAY,
                                            self.activity.id,
                                            title="testJoin")

        self.activity.add_member(user_id=self.user.id,
                                 users_count=1, price=10, free_times=0,
                                 total_fee=self.activity.price,
                                 order_id=self.order.id,
                                 order_no=self.order.order_no,
                                 payment_method=TeamOrder.OrderPaymentMethod.WXPAY,
                                 payment_state=TeamOrder.OrderState.TRADE_BUYER_SIGNED,
                                 state=TeamMember.TeamMemberState.normal)

    def test_online_pay_activity(self):
        url = self.JOIN_ACTIVITY.format(activity_id=self.activity.id)
        body = {
            "payment": "wxpay",
            "nickname": "Nick name"
        }
        self.auth_user = User.create(name='join activity')
        response = self.fetch(url, method='POST', body=json.dumps(body),
                              params={'team_id': self.team.id})
        self.assertEqual(200, response.code, response.body)

        order = TeamOrder.get_or_none(user=self.auth_user,
                                      activity_id=self.activity.id)
        self.assertIsNotNone(order, "加入活动时订单 `TeamOrder` 未创建")

        result = json.loads(response.body.decode())
        expect = {
            "status": "ok",
            "state": ActivityMember.ActivityMemberState.wait_confirm.value,
            "payment_state": TeamOrder.OrderState.WAIT_BUYER_PAY.value,
            "order_no": order.order_no
        }
        self.assertDictEqual(expect, result, result)

        member = ActivityMember.get_or_none(activity=self.activity,
                                            user=self.auth_user)
        self.assertIsNotNone(member, "加入活动后 `ActivityMember` 未添加记录")

    def test_cash_pay(self):
        activity = Activity.create(team=self.team, creator=self.creator,
                                   price='10', vip_price='8',
                                   leader=self.creator,
                                   payment_type=Activity.PaymentType.CASH_PAY,
                                   title='no online pay',
                                   description='on need online pay',
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   join_end="4000-01-01 22:59:59",
                                   max_members=10)

        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        body = {
            "payment": TeamOrder.OrderPaymentMethod.WXPAY.value,
            "nickname": "Nick name"
        }
        self.auth_user = User.create(name='no need online pay')
        response = self.fetch(url, method='POST', body=json.dumps(body),
                              params={'team_id': self.team.id})
        result = json.loads(response.body.decode())
        expect = {
            "status": "ok",
            "state": ActivityMember.ActivityMemberState.confirmed.value,
            "payment_state": TeamOrder.OrderState.WAIT_BUYER_PAY.value,
            "order_no": ""
        }
        self.assertDictEqual(expect, result, result)

        self.assertEqual(200, response.code, response.body)
        with self.assertRaises(TeamOrder.DoesNotExist):
            TeamOrder.get(user=self.auth_user, activity_id=activity.id,
                          )
        member = ActivityMember.get(activity=activity,
                                    user=self.auth_user)

        # 现在支付, 直接确认
        self.assertEqual(ActivityMember.ActivityMemberState.confirmed.value,
                         member.state, member.state)

    def create_free_activity(self, payment_type):
        """
        创建不同支付类型的免费活动
        """
        activity = Activity.create(
            team=self.team,
            creator=self.creator,
            price='0',
            vip_price='0',
            leader=self.creator,
            payment_type=payment_type,
            title='no online pay',
            description='on need online pay',
            start_time='3000-01-01 00:00:01',
            end_time='3016-12-31 23:59:59',
            join_end="3016-12-30 22:59:59",
            max_members=100
        )

        return activity

    def test_online_free_activity(self):
        """
        参加免费活动不需要支付
        线上支付活动的 ActivityMember.state 应该为 `待确认` wait_confirm
        """

        activity = self.create_free_activity(
            payment_type=Activity.PaymentType.ONLINE_PAY.value
        )

        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        body = {
            "payment": TeamOrder.OrderPaymentMethod.WXPAY.value,
            "nickname": "Nick name"
        }

        self.auth_user = User.create(name='free activity')
        response = self.fetch(url, method='POST', body=json.dumps(body),
                              params={'team_id': self.team.id})
        self.assertEqual(200, response.code, response.body)
        result = json.loads(response.body.decode())
        expect = {
            "status": "ok",
            "state": ActivityMember.ActivityMemberState.wait_confirm.value,
            "payment_state": TeamOrder.OrderState.TRADE_BUYER_PAID.value,
            "order_no": ""
        }
        self.assertDictEqual(expect, result, result)

        with self.assertRaises(TeamOrder.DoesNotExist):
            TeamOrder.get(user=self.auth_user, activity_id=activity.id)

        member = ActivityMember.get(activity=activity, user=self.auth_user)
        self.assertEqual(ActivityMember.ActivityMemberState.wait_confirm.value,
                         member.state, member.state)

    def test_cash_free_activity(self):
        """
        参加免费活动不需要支付
        线下支付活动的 ActivityMember.state 应该为 `确认` confirmed
        """

        activity = self.create_free_activity(
            payment_type=Activity.PaymentType.CASH_PAY.value
        )

        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        body = {
            "payment": TeamOrder.OrderPaymentMethod.WXPAY.value,
            "nickname": "Nick name"
        }

        self.auth_user = User.create(name='free activity')
        response = self.fetch(url, method='POST', body=json.dumps(body),
                              params={'team_id': self.team.id})
        self.assertEqual(200, response.code, response.body)
        result = json.loads(response.body.decode())
        expect = {
            "status": "ok",
            "state": ActivityMember.ActivityMemberState.confirmed.value,
            "payment_state": TeamOrder.OrderState.TRADE_BUYER_PAID.value,
            "order_no": ""
        }
        self.assertDictEqual(expect, result, result)

        with self.assertRaises(TeamOrder.DoesNotExist):
            TeamOrder.get(user=self.auth_user, activity_id=activity.id)

        member = ActivityMember.get(activity=activity, user=self.auth_user)
        self.assertEqual(ActivityMember.ActivityMemberState.confirmed.value,
                         member.state, member.state)

    def test_closed_activity(self):
        """活动已经取消或结束"""
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team, creator=self.creator,
                                   price='10', vip_price='10',
                                   leader=self.creator,
                                   payment_type=payment,
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.closed.value,
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   join_end="3000-12-30 22:59:59",
                                   )

        body = {
            "payment": "wxpay",
            "nickname": "Nick name"
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body),
                              params={'team_id': self.team.id})

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("活动已经取消或结束", error, error)

    def test_canceled_activity(self):
        """场次已取消或结束"""
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team, creator=self.creator,
                                   price='10', vip_price='10',
                                   leader=self.creator,
                                   payment_type=payment,
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.cancelled.value,
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   join_end="3016-12-30 22:59:59",)

        body = {
            "payment": "wxpay",
            "nickname": "Nick name"
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body),
                              params={'team_id': self.team.id})

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("活动已经取消或结束", error, error)

    def test_stoped_activity(self):
        """活动已报名截止"""
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team,
                                   creator=self.creator,
                                   leader=self.creator,
                                   price='10', vip_price='10',
                                   start_time='2000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   join_end="3000-12-30 22:59:59",
                                   payment_type=payment,
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.opening.value,
                                   )

        body = {
            "payment": "wxpay",
            "nickname": "Nick name"
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body),
                              params={'team_id': self.team.id})

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("活动已报名截止", error, error)

    def test_max_member_activity(self):
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team,
                                   creator=self.creator,
                                   leader=self.creator,
                                   price='10', vip_price='10',
                                   payment_type=payment,
                                   max_members=10,
                                   members_count=10,
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.opening.value,
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   join_end="3000-12-30 22:59:59",)

        body = {
            "payment": "wxpay",
            "nickname": "Nick name"
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body),
                              params={'team_id': self.team.id})

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("活动人数已满", error, error)

    def test_over_agent_count_activity(self):
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team,
                                   creator=self.creator,
                                   leader=self.creator,
                                   price='10', vip_price='10',
                                   max_members=10,
                                   payment_type=payment,
                                   members_count=1,
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.opening.value,
                                   join_end="3000-12-30 22:59:59",)
        body = {
            "payment": "wxpay",
            "nickname": "Nick name",
            "users_count": 2,
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body))

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("报名人数不能超过 1", error, error)

    def test_over_left_count_activity(self):
        payment = Activity.PaymentType.ONLINE_PAY.value
        activity = Activity.create(team=self.team,
                                   creator=self.creator,
                                   leader=self.creator,
                                   price='10', vip_price='10',
                                   payment_type=payment,
                                   title='no online pay',
                                   description='on need online pay',
                                   state=Activity.ActivityState.opening.value,
                                   join_end="3000-12-30 22:59:59",
                                   allow_agents=10,
                                   start_time='3000-01-01 00:00:01',
                                   end_time='3000-12-31 23:59:59',
                                   members_count=2,
                                   max_members=10)

        body = {
            "payment": "wxpay",
            "nickname": "Nick name",
            "users_count": 11,
        }
        url = self.JOIN_ACTIVITY.format(activity_id=activity.id)
        self.auth_user = User.create(name='closed activity')
        response = self.fetch(url, method="POST", body=json.dumps(body),
                              params={'team_id': self.team.id},
                              headers={
                                  "Content-Type": "application/json"
        })

        self.assertEqual(400, response.code, response.body)
        result = json.loads(response.body.decode())
        error = result["error"]
        self.assertEqual("该活动只有 8 名额了", error, error)

    def test_activity_members(self):
        url = self.ACTIVITY_MEMBERS.format(activity_id=self.activity.id)
        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())

    def test_activity_member_detail(self):
        member = ActivityMember.get(activity=self.activity,
                                    user=self.user)
        url = self.MEMBER_DETAIL.format(activity_id=self.activity.id,
                                        member_id=member.id)
        self.auth_user = self.creator
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())

        self.auth_user = User.create(name="permission deny")
        response = self.fetch(url)
        self.assertEqual(403, response.code, response.body.decode())


class LeaveActivityTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, Activity,
                       ActivityMember, TeamOrder]
    LEAVE_ACTIVITY = 'api/2/activities/{activity_id}/leave'

    def setUp(self):
        super(LeaveActivityTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        self.team_owner = User.create(name='test_activity')
        self.team = Team.create(name='club_test_activity',
                                owner_id=self.team_owner.id)
        self.user = self.creator = User.create(name='activity_creator')
        self.activity = Activity.create(team=self.team, creator=self.creator,
                                        price='10', vip_price='8',
                                        leader=self.creator,
                                        title='just a test',
                                        description='description',
                                        need_nickname=True,
                                        join_end="3000-12-30 22:59:59",
                                        max_members=10,
                                        start_time='3000-01-01 00:00:01',
                                        end_time='3000-12-31 23:59:59')
        self.activity_2 = Activity.create(team=self.team, creator=self.creator,
                                          price='10', vip_price='8',
                                          leader=self.creator,
                                          title='just a test',
                                          description='description',
                                          need_nickname=True,
                                          join_end="3000-12-30 22:59:59",
                                          max_members=10,
                                          start_time='3000-01-01 00:00:01',
                                          end_time='3000-12-31 23:59:59')
        self.activity_member = ActivityMember.create(
            activity=self.activity,
            user=self.user,
            total_fee='0.01',
            nickname="leave activities",
            payment_method=TeamOrder.OrderPaymentMethod.WXPAY.value,
            payment_state=TeamOrder.OrderState.TRADE_BUYER_PAID,
        )
        TeamMemberService.new_order(team=self.team,
                                    activity_id=self.activity.id,
                                    user=self.user,
                                    order_type=TeamOrder.OrderType.ACTIVITY,
                                    payment_method='wxpay',
                                    total_fee=self.activity.price,
                                    payment_fee=self.activity.price,
                                    title='TestLeave')
        TeamOrder.update(state=TeamOrder.OrderState.TRADE_BUYER_PAID)\
            .where(TeamOrder.activity_id == self.activity.id,
                   TeamOrder.user == self.user)\
            .execute()

    def test_leave(self):
        url = self.LEAVE_ACTIVITY.format(activity_id=self.activity.id)
        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(204, response.code, response.body.decode())

    def test_leave_not_join(self):
        url = self.LEAVE_ACTIVITY.format(activity_id=self.activity_2.id)
        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(400, response.code, response.body.decode())


class MyActivitiesTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, Activity,
                       ActivityMember, TeamOrder]
    MY_ACTIVITIES = 'api/2/users/{user_id}/activities'
    ACTIVITY_PROFILE = MY_ACTIVITIES + '/{activity_id}/profile'

    def setUp(self):
        super(MyActivitiesTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        self.team_owner = User.create(name='test_activity')
        self.team = Team.create(name='club_test_activity',
                                owner_id=self.team_owner.id)
        self.user = self.creator = User.create(name='activity_creator')
        self.activity = Activity.create(team=self.team, creator=self.creator,
                                        price='10', vip_price='8',
                                        leader=self.creator,
                                        title='just a test',
                                        description='description',
                                        need_nickname=True,
                                        max_members=10,
                                        start_time='3000-01-01 00:00:01',
                                        end_time='3000-12-31 23:59:59')

        self.activity_member = ActivityMember.create(
            activity=self.activity,
            user=self.user,
            total_fee='0.01',
            nickname="my activities"
        )

    def test_get_my_activities(self):
        url = self.MY_ACTIVITIES.format(user_id=self.user.id)
        response = self.fetch(url)

        self.assertEqual(200, response.code, response.body)

    def test_get_activity_profile(self):
        url = self.ACTIVITY_PROFILE.format(user_id=self.user.id,
                                           activity_id=self.activity.id)
        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body)

    def test_patch_activity_profile(self):
        url = self.ACTIVITY_PROFILE.format(user_id=self.user.id,
                                           activity_id=self.activity.id)
        body = {
            "nickname": "new nick"
        }
        self.auth_user = self.user
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body)
        updated = ActivityMember.get(activity=self.activity.id,
                                     user=self.user)
        self.assertEqual("new nick", updated.nickname)


if __name__ == '__main__':
    unittest.main()
