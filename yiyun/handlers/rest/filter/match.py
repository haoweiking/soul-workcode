from yiyun.libs.peewee_filter import (SortFilter, Filtering, Filter,
                                      StringFiltering, NumberFiltering)
from yiyun.models import MatchComment


class MatchCommentSortFilter(SortFilter):

    created = Filtering(source=MatchComment.created)
    id = Filtering(source=MatchComment.id)

    class Meta:
        ordering = ("-created", "-id")


class MatchSearchFilter(Filter):
    state = NumberFiltering(source="state")
    city = StringFiltering(source="city")

    class Meta:
        fields = ("state", "city")


class MatchMemberFilter(Filter):
    state = NumberFiltering(source="state")
    name = StringFiltering(source="name", lookup_type="regexp")

    class Meta:
        fields = ("state", "name")


