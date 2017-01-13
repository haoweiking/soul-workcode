from .base import AdminBaseHandler, admin_app

from yiyun.models import ChinaCity, Announce


@admin_app.route(r"", name="admin_home_redirect")
class HomeRedirectHandler(AdminBaseHandler):

    def get(self):
        self.redirect(self.reverse_url("admin_home"))


@admin_app.route(r"/", name="admin_home")
class HomeHandler(AdminBaseHandler):
    """docstring for HomeHandler"""

    def get(self):

        self.render("home.html")


@admin_app.route(r"/common/china_cities", name="admin_china_cities")
class ChinaCitiesHandler(AdminBaseHandler):

    def get(self):
        self.write(ChinaCity.get_cities())


@admin_app.route(r"/help", name="admin_help")
class FaqHandler(AdminBaseHandler):

    def get(self):
        self.render("faq.html")
