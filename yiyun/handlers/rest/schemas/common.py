# #! /usr/bin/env python
#
# from voluptuous import Schema, REMOVE_EXTRA, Invalid
#
# from yiyun.ext.upload_token import factory
#
#
# def action_validator(value):
#     if value in factory.generators.keys():
#         return value
#     raise Invalid('无效 action {0}'.format(value))
#
#
# request_token = Schema({
#     'action': action_validator
# }, required=True, extra=REMOVE_EXTRA)

