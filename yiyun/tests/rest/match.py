import json
import random
import unittest
from unittest import mock
from faker import Faker
from mixer.backend.peewee import mixer

from ..base import AsyncAPITestCase
from yiyun.libs.parteam import ParteamUser, Parteam
from yiyun.models import (Sport, User, Team, Match, MatchStatus,
                          MatchMember, MatchRound, MatchRound,
                          MatchAgainst, TeamOrder)
from yiyun.ext.parteam import ParteamMixin


class MatchTestCase(AsyncAPITestCase):

    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [Sport, User, Team, TeamOrder, Match, MatchMember,
                       MatchStatus, MatchRound, MatchAgainst]

    MATCH_PATH = "api/2/matches"
    MATCH_OBJECT_PATH = MATCH_PATH + "/{match_id}"
    JOIN_MATCH = MATCH_OBJECT_PATH + "/join"
    LEAVE_MATCH = MATCH_OBJECT_PATH + "/leave"
    MEMBERS_PATH = MATCH_OBJECT_PATH + "/members"

    def setUp(self):
        super(MatchTestCase, self).setUp()
        self.initial_data()

    def initial_data(self):
        faker = Faker()
        sport = Sport.create(name=faker.pystr(), description="测试")
        self.team_owner = User.create(name='test_match')
        self.team = Team.create(name='club_test_match',
                                owner_id=self.team_owner.id,
                                sport=sport)
        self.user = self.creator = User.create(name='match_creator')
        self.match = Match.create(team_id=self.team.id,
                                  user_id=self.user.id,
                                  sport_id=sport.id,
                                  price=10,
                                  title='just a test',
                                  description='description',
                                  start_time='3000-01-01 00:00:01',
                                  end_time='3000-12-31 23:59:59',
                                  join_start="2016-01-01 00:00:01",
                                  join_end="2999-12-31 23:59:59",
                                  state=Match.MatchState.opening.value,
                                  )

    def test_get_matches(self):
        params = {"sport": "1,2,3", "city": "成都市,绵阳市",
                  "province": "四川省, 北京市"}
        response = self.fetch("api/2/matches",  params=params)
        self.assertEqual(200, response.code, response.body.decode())
        # result = json.loads(response.body.decode())

    def test_get_match(self):
        response = self.fetch("api/2/matches/{0}/rounds".format(self.match.id))
        self.assertEqual(200, response.code, response.body)
        # result = json.loads(response.body.decode())

    def test_leave_match(self):
        faker = Faker()
        mocked_user = {"userId": 192, "ptToken": faker.pystr(),
                       "nickName": faker.name(), "userHeadPicUrl": faker.url()}

        mocked_parteam = mock.Mock(spec=ParteamMixin.get_session,
                                   return_value=mocked_user)
        ParteamMixin.get_session = mocked_parteam

        team_order = mixer.blend(TeamOrder,
                                 order_no=TeamOrder.get_new_order_no(),
                                 total_fee=0.01)
        mixer.blend(MatchMember, match_id=self.match.id,
                    user_id=mocked_user["userId"], group_id=0,
                    order_id=team_order.id,
                    total_fee=0.01)
        mocked_refund = mock.Mock(spec=Parteam.order_refund,
                                  return_value=True)
        Parteam.order_refund = mocked_refund

        url = self.LEAVE_MATCH.format(match_id=self.match.id)
        body = {}
        self.auth_user = ParteamUser(mocked_user)
        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body.decode())

    def parteam_user_generator(self, uid: int) -> ParteamUser:
        faker = Faker()
        _fake = {"userId": uid, "ptToken": faker.pystr(),
                 "nickName": faker.name(), "userHeadPicUrl": faker.url()}
        fake_user = ParteamUser(_fake)
        return fake_user

    def test_get_members(self):
        total = random.randint(1, 10)
        fake_users = {}
        for i in range(1, total + 1):
            parteam_user = self.parteam_user_generator(i)
            fake_users[i] = parteam_user

            order = mixer.blend(TeamOrder,
                                order_no=TeamOrder.get_new_order_no(),
                                total_fee=0.01)
            mixer.blend(MatchMember, match_id=self.match.id,
                        user_id=parteam_user.id, order_id=order.id,
                        extra_attrs={}, total_fee=0.01)

        mocked_parteam_user = mock.Mock(Parteam.parteam_user,
                                        return_value=fake_users)
        Parteam.parteam_user = mocked_parteam_user

        url = self.MEMBERS_PATH.format(match_id=self.match.id)
        response = self.fetch(url, method="GET")
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual(total, len(result["members"]), result)


if __name__ == '__main__':
    unittest.main()
