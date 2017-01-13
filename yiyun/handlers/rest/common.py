from yiyun.libs.china_cities import china_cities

from .base import (rest_app, BaseClubAPIHandler, authenticated,
                   validate_arguments_with, ApiException)

from yiyun.models import Sport


@rest_app.route("/common/china_cities")
class ChinaCities(BaseClubAPIHandler):

    """ 中国城市
    """

    def get(self):
        self.write({"china_cities": china_cities})


@rest_app.route("/common/sports")
class Sports(BaseClubAPIHandler):
    """docstring for Sports"""

    def get(self):

        query = Sport.select().order_by(Sport.sort.desc())

        sports = []
        for sport in query:
            sports.append(sport.info)

        self.write({"sports": sports})
