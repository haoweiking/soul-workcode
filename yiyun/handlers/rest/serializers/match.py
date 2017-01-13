from yiyun.core import current_app as app
from yiyun.libs.peewee_serializer import Serializer, SerializerField
from yiyun.libs.parteam import Parteam
from yiyun.models import Match, MatchStatus, MatchComment
from .user import UserSimpleSerializer
from .team import MiniTeamSerializer


class SimpleMatchSerializer(Serializer):

    team = MiniTeamSerializer(source='team')

    class Meta:
        #  only = (Match.id, Match.name)
        exclude = (Match.geohash, Match.cover_key, Match.description,
                   Match.rules, Match.fields, Match.contact,
                   Match.duration, Match.location, Match.wait_review_for_match)

        extra_attrs = ('cover', 'icon', 'open_for_join', 'state_name')


class MatchSerializer(Serializer):

    team = MiniTeamSerializer(source='team')

    class Meta:
        exclude = (Match.geohash, Match.cover_key, Match.location,
                   Match.duration, Match.contact, Match.fields,
                   Match.wait_review_for_match)

        extra_attrs = ('cover', 'icon', 'open_for_join', 'state_name')


class MatchCommentSerializer(Serializer):

    user = SerializerField(source="get_user_info")

    class Meta:
        exclude = (MatchComment.user_id,)
        recurse = False

    def __init__(self, *args, **kwargs):
        super(MatchCommentSerializer, self).__init__(*args, **kwargs)
        self.partem_users = kwargs.get("parteam_users", {})

    def get_user_info(self):
        user = self.partem_users.get(self.instance.user_id, None)
        if not user:
            return {}
        return user.secure_info


class MatchStatusSimpleSerializer(Serializer):
    photos = SerializerField(source="get_photos")

    class Meta:
        exclude = (MatchStatus.photos,)
        recurse = False

    def get_photos(self):
        keys = self.instance.photos  # type: list
        cover_url = app.settings["attach_url"]
        photos = []
        for key in keys:
            url = self.instance.get_cover_urls(cover_key=key,
                                               cover_url=cover_url)
            photos.append(url)
        return photos


class MatchStatusSerializer(MatchStatusSimpleSerializer):
    likes = SerializerField(source="get_likes")
    comments = SerializerField(source="get_comments")

    def __init__(self, *args, **kwargs):
        super(MatchStatusSerializer, self).__init__(*args, **kwargs)
        self.parteam_users = kwargs.get("parteam_users", None)

    class Meta:
        exclude = (MatchStatus.photos,)
        recurse = False
        backrefs = True

    def get_comments(self):
        comments = []
        comments_prefetch = getattr(self.instance, "comments_prefetch", [])
        for row in comments_prefetch:
            comments.append(MatchCommentSerializer(row, **self.kwargs).data)
        return comments

    def get_likes(self):
        # likes_prefetch = self.instance.likes_prefetch
        likes_prefetch = getattr(self.instance, "like_prefetch", [])
        likes = [self.parteam_users[user.user_id].secure_info for user
                 in likes_prefetch]
        return likes
