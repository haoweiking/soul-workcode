
from yiyun.ext.routing import route

from yiyun.core import current_app as app
from yiyun.handlers import BaseHandler
from yiyun.models import User

web_app = route(prefix="")


class WebBaseHandler(BaseHandler):

    def get_template_path(self):
        return self.application.settings.get("template_path") + "/web"
