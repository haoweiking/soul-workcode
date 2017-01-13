import json
import mimetypes
from io import StringIO
import unittest
from ..base import AsyncAPITestCase
from yiyun.models import (User, Team, TeamMember, TeamMemberGroup,
                          Sport, Activity,
                          ActivityMember, TeamOrder)


def encode_multipart_formdata(fields={}, files={}):
    """构造表单数据"""

    BOUNDARY = "-------tHISiStheMulTIFoRMbOUNDaRY"

    CRLF = "\r\n"
    L = []
    for (key, value) in fields.items():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)

    for key in files:
        fileinfo = files[key]
        filename = fileinfo["filename"]
        value = fileinfo["value"]

        content_type = mimetypes.guess_type(filename)[0]
        if not mimetypes.guess_type(filename)[0]:
            content_type = "application/octet-stream"

        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"'
                 % (key, filename))
        L.append("Content-Type: %s" % content_type)
        L.append("")
        L.append(value)

    L.append("--" + BOUNDARY + "--")
    L.append("")
    b = StringIO()
    for l in L:
        b.write(l)
        b.write(CRLF)

    body = b.getvalue()
    content_type = "multipart/form-data; boundary=%s" % BOUNDARY
    return content_type, body


class TeamTestCase(AsyncAPITestCase):
    RETAIN_DATA = False
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, TeamMemberGroup,
                       Activity, ActivityMember, TeamOrder]
    MODEL_PATH = 'api/2/teams'
    OBJECT_PATH = 'api/2/teams/{team_id}'
    JOIN_TEAM = OBJECT_PATH + '/join'
    LEAVE_TEAM = OBJECT_PATH + '/leave'
    TEAM_MEMBERS = OBJECT_PATH + '/members'
    MEMBER_DETAIL = TEAM_MEMBERS + '/{user_id}'
    UPDATE_ICON = OBJECT_PATH + '/icon'

    def setUp(self):
        super(TeamTestCase, self).setUp()
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
                                        description='description')

    def test_create_team(self):
        body = {
            "name": "test create team",
            "description": "description",
            "notice": "club notice",
            "province": "四川",
            "city": "成都",
            "address": "天府三街",
            "contact_person": "contact person",
            "contact_phone": "contact phone",
            "lat": 123.0000001,
            "lng": 123.0000002,
            "open_type": 2,
            "state": 1,
        }
        self.auth_user = User.create(name="create team")
        response = self.fetch(self.MODEL_PATH, method="POST",
                              body=json.dumps(body))
        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())

        self.assertEqual(0, result['state'])
        self.assertEqual(self.auth_user.id, result['owner_id'],
                         "创建俱乐部时 owner 错误")

        body.pop('state')
        for k, v in body.items():
            self.assertEqual(v, result[k], (k, v))

    def test_list_all_teams(self):
        response = self.fetch(self.MODEL_PATH)
        self.assertEqual(200, response.code, response.body)

    def test_get_object_detail(self):
        url = self.OBJECT_PATH.format(team_id=self.team.id)

        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body)

        insecrets_fields = ('wx_access_token', 'wx_expires_in', 'wx_func_info',
                            'wx_appid', 'wx_refresh_token')
        result = json.loads(response.body.decode())
        for field in insecrets_fields:
            self.assertNotIn(field, result, field)

    def test_patch_team(self):
        url = self.OBJECT_PATH.format(team_id=self.team.id)
        body = {
            "name": "new test create team",
            "description": "new description",
            "notice": "new notice",
            "province": "四川省",
            "city": "成都市",
            "address": "天府四街",
            "contact_person": "new contact person",
            "contact_phone": "new contact phone",
            "lat": 123.0,
            "lng": 123.0,
            "open_type": 1,
            "state": 2,
        }

        self.auth_user = self.team_owner
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body.decode())
        updated = Team.get(id=self.team.id)

        self.assertEqual(0, updated.state, "状态被修改了")
        body.pop("state")
        for k, v in body.items():
            self.assertEqual(v, getattr(updated, k), k)

    def test_patch_team_permission_deny(self):
        url = self.OBJECT_PATH.format(team_id=self.team.id)
        body = {
            "name": "new name"
        }
        self.auth_user = User.create(name="permission deny for patch team")
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(403, response.code, response.body.decode)

        updated = Team.get(id=self.team.id)
        self.assertNotEqual("new name", updated.name, "权限错误, 但是跟新成功了")

    def test_join_team(self):
        url = self.JOIN_TEAM.format(team_id=self.team.id)
        body = {
            "nick": "nick name",
        }
        self.auth_user = self.user
        response = self.fetch(url, method='POST', body=json.dumps(body))
        self.assertEqual(200, response.code, response.body)
        member = TeamMember.get_or_none(team=self.team, user=self.auth_user)
        self.assertIsNotNone(member, "添加俱乐部会员失败了, 没有插入 `TeamMember`")
        self.assertEqual("nick name", member.nick, member.nick)
        self.assertEqual(None, member.inviter, member.inviter)

    def test_invite_join_team(self):
        url = self.JOIN_TEAM.format(team_id=self.team.id)
        body = {
            "nick": "nick name",
            "inviter": self.team_owner.id
        }
        self.auth_user = self.user
        response = self.fetch(url, method='POST', body=json.dumps(body))
        self.assertEqual(200, response.code, response.body)
        member = TeamMember.get_or_none(team=self.team, user=self.auth_user)
        self.assertIsNotNone(member, "添加俱乐部会员失败了, 没有插入 `TeamMember`")
        self.assertEqual("nick name", member.nick, member.nick)
        self.assertEqual(self.team_owner, member.inviter, member.inviter)

    def test_leave_team(self):
        self.team.add_member(user_id=self.user.id, role=Team.TeamRole.member)
        url = self.LEAVE_TEAM.format(team_id=self.team.id)

        self.auth_user = self.user
        response = self.fetch(url)
        self.assertEqual(204, response.code, response.body.decode())

    def test_get_team_members(self):
        insecure_fields = ("inviter", "role", "push_enabled", "credit",
                           "credit_limit", "free_times", "total_recharge",
                           "created", "last_update_tim")
        user = User.create(name="leave team")
        self.team.add_member(user_id=user.id)
        url = self.TEAM_MEMBERS.format(team_id=self.team.id)

        self.auth_user = user
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("members", result, result)
        for insecure in insecure_fields:
            self.assertNotIn(insecure, result["members"][0], insecure)

    def test_get_team_member_detail(self):
        insecure_fields = ("inviter", "role", "push_enabled", "credit",
                           "credit_limit", "free_times", "total_recharge",
                           "created")
        self.team.add_member(user_id=self.user.id)
        member = TeamMember.get(team=self.team, user=self.user)
        url = self.MEMBER_DETAIL.format(team_id=self.team.id,
                                        user_id=self.user.id)

        # insecure
        self.auth_user = User.create(name="insecure")
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body)
        result = json.loads(response.body.decode())
        self.assertEqual(member.nick, result['nick'], result)
        for insecure in insecure_fields:
            self.assertNotIn(insecure, result, insecure)

    def test_get_team_member_insecure_detail(self):
        insecure_fields = ("inviter", "role", "push_enabled", "credit",
                           "credit_limit", "free_times", "total_recharge")

        self.team.add_member(user_id=self.user.id)
        member = TeamMember.get(team=self.team, user=self.user)
        url = self.MEMBER_DETAIL.format(team_id=self.team.id,
                                        user_id=self.user.id)
        # secure
        self.auth_user = self.user
        response = self.fetch(url)
        result = json.loads(response.body.decode())
        for insecure in insecure_fields:
            self.assertIn(insecure, result, insecure)

    def test_patch_member_info(self):
        self.team.add_member(user_id=self.user.id)
        member = TeamMember.get(team=self.team, user=self.user)
        url = self.MEMBER_DETAIL.format(team_id=self.team.id,
                                        user_id=self.user.id)
        body = {
            "nick": "nick name"
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body)

    def test_patch_with_group(self):
        group = TeamMemberGroup.create(team=self.team, name="test group")
        self.team.add_member(user_id=self.user.id)
        member = TeamMember.get(team=self.team, user=self.user)
        url = self.MEMBER_DETAIL.format(team_id=self.team.id,
                                        user_id=self.user.id)
        body = {
            "group_id": group.id,
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body)
        updated = TeamMember.get(user=self.user.id)
        self.assertEqual(updated.group_name, group.name, updated)
        self.assertEqual(updated.groups.first(), group, updated.groups.first())

    def test_patch_group_not_exist(self):
        self.team.add_member(user_id=self.user.id)
        member = TeamMember.get(team=self.team, user=self.user)
        url = self.MEMBER_DETAIL.format(team_id=self.team.id,
                                        user_id=self.user.id)
        body = {
            "group_id": 10000
        }
        self.auth_user = self.team_owner
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(400, response.code, response.body)


class TeamGroupTestCase(AsyncAPITestCase):
    """
    俱乐部分组
    """
    RETAIN_DATA = True
    json_header = True
    REQUIRED_MODELS = [User, Sport, Team, TeamMember, TeamMemberGroup,
                       Activity, ActivityMember, TeamOrder]
    MODEL_PATH = 'api/2/teams/{team_id}/member_groups'
    OBJECT_PATH = MODEL_PATH + "/{group_id}"

    def setUp(self):
        super(TeamGroupTestCase, self).setUp()
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
                                        start_time='3000-01-01 00:00:01',
                                        end_time='3000-12-31 23:59:59')

        self.default_group = TeamMemberGroup.create(team=self.team,
                                                    name="default group")

    def test_list_all_group(self):
        url = self.MODEL_PATH.format(team_id=self.team.id)
        self.auth_user = self.team_owner
        response = self.fetch(url)
        self.assertEqual(200, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertIn("groups", result)

    def test_create_group(self):
        url = self.MODEL_PATH.format(team_id=self.team.id)
        body = {"name": "group name"}
        self.auth_user = self.team_owner
        response = self.fetch(url, method="POST", body=json.dumps(body))
        self.assertEqual(201, response.code, response.body.decode())
        result = json.loads(response.body.decode())
        self.assertEqual("group name", result["name"], result)
        self.assertEqual(self.team.id, result["team_id"], result)

        group = TeamMemberGroup.get_or_none(team=self.team, id=result["id"])
        self.assertIsNotNone(group, "新建分组失败")
        self.assertEqual(0, group.members.count())

    def test_patch_group(self):
        url = self.OBJECT_PATH.format(team_id=self.team.id,
                                      group_id=self.default_group.id)
        body = {"name": "new name"}
        self.auth_user = self.team_owner
        response = self.fetch(url, method="PATCH", body=json.dumps(body))
        self.assertEqual(204, response.code, response.body.decode())

        updated = TeamMemberGroup.get(id=self.default_group.id)
        self.assertEqual("new name", updated.name, "修改分组名失败了")

    def test_delete_group(self):
        url = self.OBJECT_PATH.format(team_id=self.team.id,
                                      group_id=self.default_group.id)
        self.auth_user = self.team_owner
        response = self.fetch(url, method="DELETE")
        self.assertEqual(204, response.code, response.body.decode())

    def test_delete_group_with_members(self):
        user = User.create(name="add to group members")
        self.team.add_member(user.id)
        member = self.team.get_member(team_id=self.team.id, user_id=user.id)
        self.default_group.members.add(member)
        url = self.OBJECT_PATH.format(team_id=self.team.id,
                                      group_id=self.default_group.id)
        self.auth_user = self.team_owner
        response = self.fetch(url, method="DELETE")
        self.assertEqual(409, response.code, response.body.decode())


if __name__ == '__main__':
    unittest.main()
