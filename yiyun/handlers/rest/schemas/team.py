from voluptuous import Schema, REMOVE_EXTRA, Required, Coerce


join_team = Schema({
    Required("nick", default=""): str,
    Required("inviter", default=None): Coerce(int)
}, extra=REMOVE_EXTRA)


patch_member = Schema({
    "nick": str,
    "group_id": Coerce(int)
}, required=False, extra=REMOVE_EXTRA)


# 创建俱乐部的 Schema,
create_team = Schema({
    Required("name", msg="俱乐部名称必填"): str,
    "description": str,
    "notice": str,
    Required("country", default="中国"): str,
    "province": str,
    "city": str,
    "address": str,
    "contact_person": str,
    "contact_phone": str,
    "lat": Coerce(float),
    "lng": Coerce(float),
    Required("open_type", default=0): Coerce(int),
}, extra=REMOVE_EXTRA)


# 修改俱乐部, 仅部分字段可更改
patch_team = Schema({
    "name": str,
    "description": str,
    "notice": str,
    "country": str,
    "province": str,
    "city": str,
    "address": str,
    "contact_person": str,
    "contact_phone": str,
    "lat": Coerce(float),
    "lng": Coerce(float),
    "open_type": Coerce(int),
}, extra=REMOVE_EXTRA)


create_group = Schema({
    "name": str
}, required=True, extra=REMOVE_EXTRA)
