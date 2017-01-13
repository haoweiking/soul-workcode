from .base import ClubBaseHandler, club_app

from yiyun.models import ChinaCity, Announce, Team


@club_app.route(r"", name="club_home_redirect")
class HomeRedirectHandler(ClubBaseHandler):

    def get(self):
        self.redirect(self.reverse_url("club_home"))


@club_app.route(r"/", name="club_home")
class HomeHandler(ClubBaseHandler):
    """docstring for HomeHandler"""

    def get(self):

        announces = Announce.select().order_by(Announce.id.desc())
        announces = self.paginate_query(announces)

        members_count = Team.get_members_count(self.current_team.id)

        self.render("home.html",
                    announces=announces,
                    members_count=members_count
                    )


@club_app.route(r"/common/china_cities", name="club_china_cities")
class ChinaCitiesHandler(ClubBaseHandler):

    login_required = False
    team_required = False
    email_verified_required = False

    def get(self):
        self.write(ChinaCity.get_cities())


@club_app.route(r"/help", name="club_help")
class FaqHandler(ClubBaseHandler):

    def get(self):
        self.render("faq.html")
