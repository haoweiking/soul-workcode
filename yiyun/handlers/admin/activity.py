import logging
import hashlib
import time
from datetime import datetime

from yiyun.models import Team, Activity, User
from yiyun.helpers import intval
from .base import AdminBaseHandler, admin_app


@admin_app.route(r'/activities', name="admin_activities")
class ActivitiesHandler(AdminBaseHandler):

    def get(self):
        """获取活动列表"""

        keyword = self.get_argument("kw", "")
        state = intval(self.get_argument("state", -1))
        sort = intval(self.get_argument("sort", 0))

        query = Activity.select(
            Activity,
            Team,
        ).join(
            Team, on=(Team.id == Activity.team).alias("team")
        )

        is_restrict_by_areas = self.current_user.is_restrict_by_areas()
        if is_restrict_by_areas:
            query = query.join(
                User,
                on=(User.id == Team.owner_id)
            ).where(
                User.province << self.current_user.valid_manage_provinces
            )

        if state == 0:
            query = query.where(Activity.state == Activity.ActivityState.cancelled)

        elif state == 1:
            query = query.where(Activity.state == Activity.ActivityState.opening)

        elif state == 2:
            query = query.where(Activity.state == Activity.ActivityState.finished)

        if keyword:
            query = query.where(Activity.title.contains(keyword))

        if sort == 2:
            query = query.order_by(Activity.start_time.desc())
        else:
            query = query.order_by(Activity.id.desc())

        activities = self.paginate_query(query)

        self.render("activity/list.html",
                    activities=activities,
                    )


@admin_app.route(r"/activities/([\d]+)", name="admin_activity_detail")
class DetailHandler(AdminBaseHandler):

    def get(self, activity_id):

        activity = Activity.get_or_404(id=activity_id)
        self.render("activity/detail.html", activity=activity)

    def post(self, activity_id):

        action = self.get_argument("action")

        if action == "cancel":
            tasks.activity.cancel_activity(activity_id)

        self.write_success()
