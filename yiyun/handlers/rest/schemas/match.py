from voluptuous import Schema, Required, REMOVE_EXTRA, Optional, Coerce


new_match_comment = Schema({
    Required("content", msg="评论内容不能为空"): str,
    Optional("reply_to_comment_id"): Coerce(int),
    Optional("reply_to_user_id"): Coerce(int)
}, extra=REMOVE_EXTRA)


leave_match = Schema({
    "reason": str,
    Optional("insists", default=False): bool,
}, required=False, extra=REMOVE_EXTRA)
