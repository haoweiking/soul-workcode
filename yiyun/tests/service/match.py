"""
MatchService unittest
"""
from datetime import datetime
from random import randint
from unittest import mock

from tornado.testing import unittest
from faker import Faker
from mixer.backend.peewee import mixer

from yiyun.tests.base import AsyncModelTestCase
from yiyun.models import (User, Admin, Match, MatchMember, TeamOrder, Team,
                          Sport, SettlementApplication, ApplicationState)
from yiyun.service.match import (MatchService, SettlementApplicationException,
                                 ApplicationProcessingException,
                                 SettlementApplicationExist,
                                 SettlementService, MatchStateError)
from yiyun.tasks.match import settlement


class MatchServiceTestCase(AsyncModelTestCase):
    """
    MatchService TestCase
    """

    RETAIN_DATA = False
    REQUIRED_MODELS = [Sport, Team, User, TeamOrder, Match, MatchMember]

    def setUp(self):
        super(MatchServiceTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        faker = Faker()
        self.sport = mixer.blend(Sport, name=faker.pystr())

    def test_members_function(self):
        faker = Faker()
        match = mixer.blend(Match)
        mixer.blend(MatchMember, match_id=match.id, user_id=faker.random_int(),
                    total_fee=0.01)
        mixer.blend(MatchMember, match_id=match.id, user_id=faker.random_int(),
                    total_fee=0.01)
        members = MatchService.members(match)
        self.assertEqual(2, len(members))
        for row in members:
            self.assertEqual(match.id, row.match_id)

    def test_cancel(self):
        faker = Faker()
        user = mixer.blend(User)
        team = mixer.blend(Team, sport=self.sport)
        match = mixer.blend(Match, state=Match.MatchState.opening.value,
                            team_id=team.id)
        total_fee = 10.01
        total_members = randint(1, 10)
        for _ in range(0, total_members):
            order = mixer.blend(TeamOrder, team=team, user=user,
                                order_no=TeamOrder.get_new_order_no(),
                                total_fee=total_fee, payment_fee=total_fee)
            mixer.blend(MatchMember, match_id=match.id, total_fee=total_fee,
                        order_id=order.id, pt_order_no=faker.pystr())

        MatchService.cancel(match, user)

    def test_cancel_already_canceled(self):
        user = mixer.blend(User)
        match = mixer.blend(Match, state=Match.MatchState.cancelled)
        with self.assertRaises(MatchStateError):
            MatchService.cancel(match, user)


class SettlementApplicationTestCase(AsyncModelTestCase):

    RETAIN_DATA = True
    REQUIRED_MODELS = [User, Admin, Match, SettlementApplication]

    def test_new_application(self):
        match = mixer.blend(Match)
        user = mixer.blend(User)
        MatchService.settlement_application(user=user, match=match)

    # def test_new_application_match_finished(self):
    #     match = mixer.blend(Match, finished=datetime.now())
    #     user = mixer.blend(User)
    #     with self.assertRaises(SettlementApplicationException):
    #         MatchService.settlement_application(user, match)

    def test_new_application_approved(self):
        user = mixer.blend(User)
        match = mixer.blend(Match)
        application = mixer.blend(SettlementApplication, match_id=match.id,
                                  user_id=user.id)
        with self.assertRaises(SettlementApplicationExist):
            MatchService.settlement_application(user, match)

    def test_approve(self):
        mocked_settlement = mock.Mock(spec=settlement.delay, return_value=1)
        settlement.delay = mocked_settlement
        admin = mixer.blend(Admin)
        application = mixer.blend(SettlementApplication,
                                  processing=ApplicationState.requesting.value)
        SettlementService.approve(application, admin)

        approved = SettlementApplication.get(id=application.id)
        self.assertEqual(ApplicationState.approved.value, approved.processing,
                         "审核后状态错误")
        self.assertEqual(admin.id, approved.admin_id, "审核人 ID 错误")

    def test_approve_processing_error(self):
        admin = mixer.blend(Admin)
        application = mixer.blend(SettlementApplication,
                                  processing=ApplicationState.approved.value)
        with self.assertRaises(ApplicationProcessingException):
            SettlementService.approve(application, admin)

        approved = SettlementApplication.get(id=application.id)
        self.assertEqual(application.processing, approved.processing,
                         "审核报错后, 申请状态发生变化")
        self.assertEqual(None, approved.admin_id, "审核人 ID 错误")

    def test_disapprove(self):
        admin = mixer.blend(Admin)
        application = mixer.blend(SettlementApplication,
                                  processing=ApplicationState.requesting.value)
        SettlementService.disapprove(application, admin)

        approved = SettlementApplication.get(id=application.id)
        self.assertEqual(ApplicationState.disapproved.value,
                         approved.processing,
                         "申请驳回失败")
        self.assertEqual(admin.id, approved.admin_id, "审核人 ID 错误")

    def test_disapprove_processing_error(self):
        admin = mixer.blend(Admin)
        application = mixer.blend(SettlementApplication,
                                  processing=ApplicationState.finished.value)
        with self.assertRaises(ApplicationProcessingException):
            SettlementService.disapprove(application, admin)

        approved = SettlementApplication.get(id=application.id)
        self.assertEqual(approved.processing, approved.processing,
                         "申请驳回报错后, 申请状态发生变化")


if __name__ == '__main__':
    unittest.main()
