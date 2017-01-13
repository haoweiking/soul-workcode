import time
import hashlib

import tornado.escape
import tornado.web

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile
from yiyun.models import Team, TeamMember, TeamMemberGroup

from yiyun import tasks


@club_app.route("/message", name="club_message")
class MessageHandler(ClubBaseHandler):
    """docstring for Members"""

    def get(self):

        self.render("message/message.html")
