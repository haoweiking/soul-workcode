from datetime import datetime, timedelta
from yiyun.core import celery, current_app as app
from yiyun.libs.parteam import (Parteam, JoinMatchDone, ParteamRequestError,
                                MatchStartMessage, RefundMessage,
                                NewMatchScheduleMessage)
from yiyun.models import Team, Match, MatchMember, MatchStartCeleryTask
from yiyun.service.match import MatchService


@celery.task(bind=True, default_retry_delay=2 * 60)
def join_match_done(self, match_id: int, member_id: int):
    """
    参加赛事完成, 调用派队消息推送接口
    :param: self: celery.task.Context
    :param match_id: int,  Match.id
    :param member_id: int, MatchMember.id
    """

    pt = Parteam(app.settings["parteam_api_url"])
    match = Match.get(id=match_id)  # type: Team
    team = Team.get(id=match.team_id)
    member = MatchMember.get(match_id=match_id, id=member_id)  # type: MatchMember
    user_info = {"mobile": member.mobile, "userId": member.user_id}
    message = JoinMatchDone(user_infos=[user_info],
                            match_fee=int(member.total_fee * 100),
                            match_id=match_id,
                            match_name=match.title,
                            sponsor_name=team.name,
                            sponsor_pic_url=team.get_cover_url(size="medium"))

    if not pt.push_message(message=message):
        raise self.retry(exc=ParteamRequestError("调用派队推送接口失败"))


@celery.task(default_retry_delay=2 * 60)
def leave_match_done(match_id: int, member_id: int):
    """
    退出赛事完成, 调用派队消息推送接口
    :param match_id:
    :param member_id:
    :return:
    """
    raise NotImplementedError()


@celery.task(default_retry_delay=60)
def scan_match_start_time():
    """
    定时扫描 Match 表, 提前两小时发送比赛开始通知
    :return:
    """
    now = datetime.now()
    max_dt = now + timedelta(hours=2)
    min_dt = now - timedelta(minutes=10)
    matches = Match.select().where(Match.pushed.is_null(),
                                   Match.start_time >= min_dt,
                                   Match.start_time <= max_dt)
    for match in matches:
        match_start.delay(match_id=match.id)
        Match.update(pushed=now).where(Match.id == match.id).execute()


@celery.task(bind=True, default_retry_delay=2 * 60)
def match_start(self, match_id: int):
    """
    赛事开始前, 调用派队消息推送接口
    :param self: celery task Context
    :param match_id:
    :return:
    """
    match = Match.get(id=match_id)  # type: Match
    team = Team.get(id=match.team_id)  # type: Team
    members = MatchService.members(match,
                                   state=MatchMember.MatchMemberState.normal)
    infos = []
    for member in members:
        infos.append({"userId": member.user_id, "mobile": member.mobile})

    message = MatchStartMessage(
        user_infos=infos, match_id=match_id, match_name=match.title,
        sponsor_name=team.name,
        sponsor_pic_url=team.get_cover_url(size="medium"))

    pt = Parteam(app.settings["parteam_api_url"])
    if not pt.push_message(message=message):
        self.retry(exc=ParteamRequestError("调用派队推送接口失败"))

    # MatchStartCeleryTask.task_done(self.request.id)


@celery.task(bind=True, default_retry_delay=2 * 60)
def match_refund(self, match_id: int, order_no: str, user_info: dict):
    """
    主办方退款推送
    :param self:
    :param match_id:
    :param order_no: 派队支付订单
    :param user_info:
    :return:
    """
    match = Match.get(id=match_id)  # type: Match
    team = Team.get(id=match.team_id)
    message = RefundMessage(user_infos=[user_info, ], order_no=order_no,
                            match_id=match_id, match_name=match.title,
                            sponsor_name=team.name,
                            sponsor_pic_url=team.get_cover_url(size="medium"))
    pt = Parteam(app.settings["parteam_api_url"])
    if not pt.push_message(message):
        self.retry(exc=ParteamRequestError("调用派队推送接口失败"))


@celery.task(bind=True, default_retry_delay=2 * 60)
def new_match_status(self, match_id: int):
    """
    主办方发布新战报时向赛事成员推送信息
    :param self:
    :param match_id:
    :return:
    """
    match = Match.get(id=match_id)  # type: Match
    team = Team.get(id=match.team_id)  # type: Team
    members = MatchService.members(match,
                                   state=MatchMember.MatchMemberState.normal)

    infos = []
    for member in members:
        infos.append({"mobile": member.mobile, "userId": member.user_id})

    message = NewMatchScheduleMessage(
        user_infos=infos, match_id=match_id, match_name=match.title,
        sponsor_name=team.name,
        sponsor_pic_url=team.get_cover_url(size="medium"))

    pt = Parteam(app.settings["parteam_api_url"])
    if not pt.push_message(message):
        self.retry(ParteamRequestError("调用派队推送接口失败"))
