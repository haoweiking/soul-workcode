from .base import BaseService, ServiceException
from yiyun.models import User, Team, TeamFollower


class UserService(BaseService):

    @classmethod
    def following_teams(cls, user_id):
        """获取用户关注的俱乐部列表"""
        query = Team.select(Team)\
            .join(TeamFollower, on=(TeamFollower.team_id == Team.id))\
            .where(TeamFollower.user_id == user_id)
        return query

