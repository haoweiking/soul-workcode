import logging
import hashlib
import time
from datetime import datetime

from yiyun.models import User
from yiyun.helpers import intval
from .base import AdminBaseHandler, admin_app


@admin_app.route(r'/users', name="admin_users")
class UsersHandler(AdminBaseHandler):

    def get(self):
        """
        获取用户列表
        """

        keyword = self.get_argument("kw", "")
        sort = intval(self.get_argument("sort", 0))

        query = User.select()

        if keyword:
            query = query.where(
                (User.name.contains(keyword)
                 ) | (User.mobile == keyword)
            )

        if sort == 2:
            query = query.order_by(User.name.desc())
        else:
            query = query.order_by(User.id.desc())

        users = self.paginate_query(query)

        self.render("user/list.html",
                    users=users,
                    )
