#!/usr/bin/python
# _*_ coding: UTF-8 _*_

###
# 本文件提供百度云服务PYTHON版本SDK的公共网络交互功能
#
# @author 百度移动.云事业部
# @copyright Copyright (c) 2012-2020 百度在线网络技术(北京)有限公司
# @version 1.0.0
# @package
##


class ResponseCore(object):

    def __init__(self, header, body, status=None):
        self.header = header
        self.body = body.decode("utf-8")
        self.status = status

    def isOK(self, codes=None):
        if codes is None:
            codes = [200, 201, 204, 206]
            return self.status in codes
        else:
            return self == codes
