import peewee

from .base import ClubBaseHandler, club_app

from yiyun.models import (Team, User, TeamFollower, Activity, ActivityMember,
                          TeamOrder)
from yiyun.helpers import intval, floatval
from yiyun.libs.parteam import Parteam


@club_app.route("/followers", name="club_followers")
class FollowersList(ClubBaseHandler):

    """
    粉丝列表
    """

    def get(self):
        parteam = Parteam(self.settings["parteam_api_url"])
        query = TeamFollower.select(TeamFollower, Team)\
            .join(Team, on=(Team.id == TeamFollower.team_id).alias("team"))\
            .where(Team.id == self.current_team.id)\
            .order_by(Team.created.desc())

        query = self.paginate_query(query)

        followers = []
        for item in query:
            followers.append(item.info)

        user_ids = [follower["user_id"] for follower in followers
                    if follower["user_id"]]
        if user_ids:
            user_infos = parteam.parteam_user(user_ids)

            for follower in followers:
                self.logger.debug(follower)
                follower["user_info"] = user_infos.get(follower["user_id"])

        self.render("follower/list.html",
                    pagination=query.pagination,
                    followers=followers)


@club_app.route("/followers/list/action", name="club_followers_list_action")
class FollowersListAction(ClubBaseHandler):

    """
    粉丝列表操作
    """

    def post(self):
        pass
