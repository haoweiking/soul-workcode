from datetime import datetime, timedelta

import geohash
import tornado.escape
import tornado.web
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from peewee import JOIN_LEFT_OUTER

from .base import ClubBaseHandler, club_app

from yiyun.exceptions import ArgumentError
from yiyun.helpers import is_mobile, intval
from yiyun.models import (fn, User, Team, Activity, ActivityMember,
                          ChinaCity, TeamMember, TeamOrder)
from yiyun.ext.mixins import AMapMixin
from .forms.activity import CreateActivityFrom

from yiyun import tasks


@club_app.route("/activities", name="club_activity_list")
class ListHandler(ClubBaseHandler):

    def get(self):

        keyword = self.get_argument("kw", "")
        filter_state = intval(self.get_argument("state", -1))
        sort = intval(self.get_argument("sort", 0))

        query = Activity.select(
            Activity,
            User
        ).join(
            User, on=(Activity.leader == User.id).alias("leader")
        ).where(
            Activity.team == self.current_team
        )

        if filter_state == 0:
            query = query.where(Activity.state == Activity.ActivityState.cancelled)

        elif filter_state == 1:
            query = query.where(Activity.state == Activity.ActivityState.opening)

        elif filter_state == 2:
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


@club_app.route(r"/activities/([\d]+)/apply_form", name="club_activity_applyform")
class ApplyFormHandler(ClubBaseHandler):

    def get(self, activity_id):

        activity = Activity.get_or_404(id=activity_id)

        members = ActivityMember.select(
            ActivityMember,
            TeamOrder,
            User
        ).join(
            User, on=(ActivityMember.user == User.id).alias("user")
        ).switch(
            ActivityMember
        ).join(
            TeamOrder,
            join_type=JOIN_LEFT_OUTER,
            on=(TeamOrder.id == ActivityMember.order_id).alias("order")
        ).where(
            ActivityMember.activity == activity
        )

        activity.total_amount = ActivityMember.select(
            fn.SUM(ActivityMember.total_fee)
        ).where(
            ActivityMember.payment_state << (TeamOrder.OrderState.TRADE_BUYER_PAID,
                                             TeamOrder.OrderState.TRADE_FINISHED),
            ActivityMember.activity == activity
        ).scalar() or 0

        members = self.paginate_query(members)

        activity.members_count = ActivityMember.select(
            fn.SUM(ActivityMember.users_count)
        ).where(
            ActivityMember.state == ActivityMember.ActivityMemberState.confirmed,
            ActivityMember.activity == activity
        ).scalar() or 0

        self.render("activity/members.html",
                    activity=activity,
                    members=members)

    def post(self, activity_id, ):
        activity = Activity.get_or_404(id=activity_id)


@club_app.route(r"/activities/([\d]+)", name="club_activity_detail")
class DetailHandler(ClubBaseHandler):

    def get(self, activity_id):

        activity = Activity.get_or_404(id=activity_id)
        self.render("activity/detail.html", activity=activity)

    def post(self, activity_id):

        action = self.get_argument("action")

        if action == "cancel":
            tasks.activity.cancel_activity(activity_id)

        self.write_success()


@club_app.route("/activities/create", name="club_activity_create")
class CreateHandler(ClubBaseHandler, AMapMixin):
    """docstring for CreateHandler"""

    def get(self):

        duplicate_id = self.get_argument("duplicate_id", None)

        if duplicate_id:
            activity = Activity.get_or_none(id=duplicate_id)
            activity.id = None

        else:
            activity = Activity(
                team=self.current_team,
                contact_person=self.current_team.contact_person,
                contact_phone=self.current_team.contact_phone,

                province=self.current_team.province,
                city=self.current_team.city,
                address=self.current_team.address
            )

        form = CreateActivityFrom(obj=activity, team=self.current_team)

        self.render("activity/new.html",
                    form=form,
                    cities=ChinaCity.get_cities())

    @tornado.gen.coroutine
    def post(self):

        form = CreateActivityFrom(self.arguments, team=self.current_team)

        if form.validate():
            activity = Activity()
            form.populate_obj(activity)

            need_fields = self.get_arguments("need_fields")
            for field in need_fields:
                setattr(activity, field, True)

            geocode = yield self.get_geocode(activity.city, activity.address)

            if geocode.get("geocodes", []):
                location = geocode['geocodes'][0]['location'].split(",")
                activity.lat = location[1]
                activity.lng = location[0]
                activity.geohash = geohash.encode(float(location[1]), float(location[0]))

            if activity.repeat_type == "week":
                activity.week_day = activity.start_time.weekday() + 1

            elif activity.repeat_type == "month":
                activity.month_day = activity.start_time.day

            activity.team = self.current_team
            activity.creator = self.current_user
            activity.save()

            # 更新俱乐部活动数量
            Team.update_activities_count(self.current_team.id)

            self.redirect(self.reverse_url("club_activity_list"))
            return

        province = self.get_argument("province", None)
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("activity/new.html",
                    form=form,
                    cities=ChinaCity.get_cities())


@club_app.route(r"/activities/([\d]+)/edit", name="club_activity_edit")
class EditHandler(ClubBaseHandler, AMapMixin):

    def get(self, activity_id):
        activity = Activity.get_or_404(id=activity_id)

        form = CreateActivityFrom(obj=activity, team=self.current_team)

        self.render("activity/edit.html",
                    form=form,
                    cities=ChinaCity.get_cities())

    @tornado.gen.coroutine
    def post(self, activity_id):

        activity = Activity.get_or_404(id=activity_id)

        form = CreateActivityFrom(self.arguments, team=self.current_team)

        if form.validate():
            form.populate_obj(activity)

            need_fields = self.get_arguments("need_fields")
            for field in need_fields:
                setattr(activity, field, True)

            geocode = yield self.get_geocode(activity.city, activity.address)

            if geocode.get("geocodes", []):
                location = geocode['geocodes'][0]['location'].split(",")
                activity.lat = location[1]
                activity.lng = location[0]
                activity.geohash = geohash.encode(float(location[1]), float(location[0]))

            if activity.repeat_type == "week":
                activity.week_day = activity.start_time.weekday() + 1

            elif activity.repeat_type == "month":
                activity.month_day = activity.start_time.day

            activity.updated = datetime.now()
            activity.save()

            self.redirect(self.reverse_url("club_activity_list"))
            return

        province = self.get_argument("province", None)
        if province:
            form.city.choices = ChinaCity.get_cities(province)

        self.render("activity/new.html",
                    form=form,
                    cities=ChinaCity.get_cities())
