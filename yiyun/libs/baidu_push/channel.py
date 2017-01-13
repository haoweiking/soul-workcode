#!/usr/bin/python
# _*_ coding: UTF-8 _*_

import time

import urllib.request
import urllib.parse
import urllib.error

import hashlib
import json
import platform

import requests

from .lib.ChannelException import ChannelException
from .lib.RequestCore import ResponseCore
from .lib.valid import validOptDict, validParam, nullOk


class Channel(object):

    # baidu push 域名
    host = 'api.tuisong.baidu.com'

    # 应用key，从百度开发者中心获得,是创建Channel的必须参数
    api_key = ''

    # 从百度开发者中心获得，是创建Channel的必须参数
    secret_key = ''

    # 设备类型，3:android, 4:ios
    device_type = ''

    DEVICE_TYPE_ANDROID = 3
    DEVICE_TYPE_IOS = 4

    # Channel常量，用于计算sign，用户不必关注
    sign = 'sign'
    method = 'method'
    request_id = None

    # Channel 错误常量
    channel_sdk_init_error = 1
    channel_sdk_running_error = 2
    channel_sdk_param = 3
    channel_sdk_http_status_ok_but_result_error = 4
    channel_sdk_http_status_error_and_result_error = 5

    # 操作系统版本信息，用于User-Agent设置
    system_info = 'system_info'

    def __init__(self, apiKey, secretKey, deviceType=3):
        """init 获得运行linux平台版本信息"""

        self.system_info = str(platform.uname())

        self.setApiKey(apiKey)
        self.setSecretKey(secretKey)
        self.setDeviceType(deviceType)

    def setApiKey(self, apiKey):
        """运行期间可以另指定apiKey

        args：
            apiKey--想要指定的apiKey"""

        self.api_key = apiKey

    def setSecretKey(self, secretKey):
        """运行期间可以另指定secretKey

        args：
            secretKey--想要指定的secretKey"""

        self.secret_key = secretKey

    def setDeviceType(self, deviceType):
        """运行期间可以修改设备类型

        args:
            deviceType--想要指定的deviceType"""

        self.device_type = deviceType

    def getRequestId(self):
        """获得服务器返回的requestId

        return:
            requestId"""

        return self.request_id

    @validParam(channel_id=str, msg=str, opts=nullOk(dict))
    def pushMsgToSingleDevice(self, channel_id, msg, opts=None):
        """向单个设备推送消息

        args:
            channel_id--客户端初始化成功之后返回的channelId
            msg--json格式的通知数据，详见说明文档
            opts--可选字段合集，详见说明文档
        return：
            msg_id--消息id
            send_time--消息的实际推送时间
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'pushMsgToSingleDevice')
        args = self._commonSet()
        args['channel_id'] = channel_id
        args['msg'] = msg
        args.update(opts)
        self._product_name = 'push'
        self._resource_name = 'single_device'

        return self._commonProcess(args)

    @validParam(msg=str, opts=nullOk(dict))
    def pushMsgToAll(self, msg, opts=None):
        """向当前app下所有设备推送一条消息

        args:
            msg--json格式的通知数据，详见说明文档
            opts--可选字段合集，详见说明文档
        return：
            msg_id--消息id
            send_time--消息的实际推送时间
            timer_id(可选)--定时服务ID
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'pushMsgToAll')
        args = self._commonSet()
        args['msg'] = msg
        args.update(opts)
        self._product_name = 'push'
        self._resource_name = 'all'

        return self._commonProcess(args)

    @validParam(type=(int, '0<x<2'), tag=str, msg=str, opts=nullOk(dict))
    def pushMsgToTag(self, tag, msg, type=1, opts=None):
        """推送消息或通知给指定的标签

        args:
            tag--已创建的tag名称
            msg--json格式的通知数据，详见说明文档
            type--推送的标签类型,目前固定值为1
            opts--可选字段合集，详见说明文档
        return：
            msg_id--消息id
            send_time--消息的实际推送时间
            timer_id(可选)--定时服务ID
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'pushMsgToTag')
        args = self._commonSet()
        args['type'] = type
        args['tag'] = tag
        args['msg'] = msg
        args.update(opts)
        self._product_name = 'push'
        self._resource_name = 'tags'

        return self._commonProcess(args)

    @validParam(channel_ids=list, msg=str, opts=nullOk(dict))
    def pushBatchUniMsg(self, channel_ids, msg, opts=None):
        """推送消息给批量设备（批量单播）

        args:
            channel_ids--一组channel_id（最多为一万个）组成的json数组字符串
            channel_ids--一组channel_id（最少1个，最多为10个）组成的list，对应一批设备
            msg--json格式的通知数据，详见说明文档
            opts--可选字段合集，详见说明文档
        return：
            msg_id--消息id
            send_time--消息的实际推送时间
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'pushBatchUniMsg')
        args = self._commonSet()
        args['channel_ids'] = json.dumps(channel_ids)
        args['msg'] = msg
        #args['topic_id'] = topic_id
        args.update(opts)
        self._product_name = 'push'
        self._resource_name = 'batch_device'

        return self._commonProcess(args)

    @validParam(msg_id=str)
    def queryMsgStatus(self, msg_id):
        """根据msg_id获取消息推送报告

        args:
            msg_id--推送接口返回的msg_id，支持一个由msg_id组成的json数组
        return：
            total_num--结果数量
            result--数组对象，每项内容为一条消息的状态
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档

        目前不支持单播msg id查询"""

        self._checkConf()

        args = self._commonSet()
        args['msg_id'] = msg_id
        self._product_name = 'report'
        self._resource_name = 'query_msg_status'

        return self._commonProcess(args)

    @validParam(timer_id=str, opts=nullOk(dict))
    def queryTimerRecords(self, timer_id, opts=None):
        """根据timer_id获取消息推送记录

        args:
            timer_id--推送接口返回的timer_id
            opts--可选字段合集，详见说明文档
        return：
            timer_id--定时任务id
            result--数组对象，每项内容为该定时任务所产生的一条消息的状态
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'queryTimerRecords')
        args = self._commonSet()
        args['timer_id'] = timer_id
        args.update(opts)
        self._product_name = 'report'
        self._resource_name = 'query_timer_records'

        return self._commonProcess(args)

    @validParam(topic_id=(str, '0<len(x)<129'), opts=nullOk(dict))
    def queryTopicRecords(self, topic_id, opts=None):
        """根据分类主题获取消息推送记录

        args:
            topic_id--分类主题名称
            opts--可选字段合集，详见说明文档
        return：
            topic_id--分类主题名称
            result--数组对象，每项内容为该分类主题下的一条消息的相关信息
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'queryTopicRecords')
        args = self._commonSet()
        args['topic_id'] = topic_id
        args.update(opts)
        self._product_name = 'report'
        self._resource_name = 'query_topic_records'

        return self._commonProcess(args)

    @validParam(opts=nullOk(dict))
    def queryTimerList(self, opts=None):
        """查看还未执行的定时任务，每个应用可设置的有效的定时任务有限制(目前为10个)

        args:
            opts--可选字段合集，详见说明文档
        return：
            total_num--定时推送任务的总数量
            result--数组对象，每项表示一个定时任务的相关信息
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'queryTimerList')
        args = self._commonSet()
        args.update(opts)
        self._product_name = 'timer'
        self._resource_name = 'query_list'

        return self._commonProcess(args)

    @validParam(opts=nullOk(dict))
    def queryTopicList(self, opts=None):
        """查询推送过程中使用过的分类主题列表

        args:
            opts--可选字段合集，详见说明文档
        return：
            total_num--所使用过的分类主题总数
            result--json数组，数组中每项内容表示一个分类主题的相关信息
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'queryTopicList')
        args = self._commonSet()
        args.update(opts)
        self._product_name = 'topic'
        self._resource_name = 'query_list'

        return self._commonProcess(args)

    @validParam(opts=nullOk(dict))
    def queryTags(self, opts=None):
        """查询应用的tag

        args:
            opts--可选字段合集，详见说明文档
        return：
            total_num--Tag总数
            result--数组对象，每项内容表示一个Tag的详细信息
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        validOptDict(opts, 'queryTags')
        args = self._commonSet()
        args.update(opts)
        self._product_name = 'app'
        self._resource_name = 'query_tags'

        return self._commonProcess(args)

    @validParam(tag=(str, '0<len(x)<129'))
    def createTag(self, tag):
        """创建一个空的标签组

        args:
            tag--标签名称
        return：
            tag--标签名称
            result--状态 0：创建成功； 1：创建失败；
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['tag'] = tag
        self._product_name = 'app'
        self._resource_name = 'create_tag'

        return self._commonProcess(args)

    @validParam(tag=(str, '0<len(x)<129'))
    def deleteTag(self, tag):
        """删除一个已存在的tag

        args:
            tag--标签名称
        return：
            tag--标签名称
            result--状态 0：删除成功； 1：删除失败；
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['tag'] = tag
        self._product_name = 'app'
        self._resource_name = 'del_tag'

        return self._commonProcess(args)

    @validParam(tag=(str, '0<len(x)<129'), channel_ids=list)
    def addDevicesToTag(self, tag, channel_ids):
        """向tag中批量添加设备

        args:
            tag--标签名称
            channel_ids--一组channel_id（最少1个，最多为10个）组成的list，对应一批设备
        return：
            devices--数组对象，每个元素表示对应的一个channel_id是否添加成功
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['tag'] = tag
        args['channel_ids'] = json.dumps(channel_ids)
        self._product_name = 'tag'
        self._resource_name = 'add_devices'

        return self._commonProcess(args)

    @validParam(tag=(str, '0<len(x)<129'), channel_ids=list)
    def deleteDevicesFromTag(self, tag, channel_ids):
        """从tag中批量解绑设备

        args:
            tag--标签名称
            channel_ids--一组channel_id（最少1个，最多为10个）组成的list，对应一批设备
        return：
            devices--数组对象，每个元素表示对应的一个channel_id是否删除成功
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['tag'] = tag
        args['channel_ids'] = json.dumps(channel_ids)
        self._product_name = 'tag'
        self._resource_name = 'del_devices'

        return self._commonProcess(args)

    @validParam(tag=(str, '0<len(x)<129'))
    def queryDeviceNumInTag(self, tag):
        """查询某个tag关联的设备数量

        args:
            tag--标签名称
        return：
            device_num--标签中设备的数量
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['tag'] = tag
        self._product_name = 'tag'
        self._resource_name = 'device_num'

        return self._commonProcess(args)

    @validParam(topic_id=(str, '0<len(x)<129'))
    def queryStatisticTopic(self, topic_id):
        """统计当前应用下一个分类主题的消息数量

        args:
            topic_id--一个已使用过的分类主题
        return：
            total_num--所发的分类主题总数
            result--dic对象，key为统计信息当天的0点0分的时间戳，value包含(ack：当天消息到达数)
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        args['topic_id'] = topic_id
        self._product_name = 'report'
        self._resource_name = 'statistic_topic'

        return self._commonProcess(args)

    def queryStatisticDevice(self):
        """统计APP 设备数

        return：
            total_num--统计结果集的条数
            result--dic对象，详见说明文档
        Exception：
            参数错误或者http错误，会抛出此异常，异常信息详见说明文档"""

        self._checkConf()

        args = self._commonSet()
        self._product_name = 'report'
        self._resource_name = 'statistic_device'

        return self._commonProcess(args)

    def _commonSet(self):
        """公共参数设置"""

        args = dict()

        args['apikey'] = self.api_key
        args['secretKey'] = self.secret_key
        args['device_type'] = self.device_type
        args['timestamp'] = int(time.time())

        return args

    def _genSign(self, method, url, arrContent):
        """签名计算"""

        gather = method + url
        keys = list(arrContent.keys())
        keys.sort()
        for key in keys:
            gather += key + '=' + str(arrContent[key])
        gather += self.secret_key
        sign = hashlib.md5(urllib.parse.quote_plus(gather).encode("utf-8"))

        return sign.hexdigest()

    def _baseControl(self, opt):
        """http交互"""
        url = 'http://' + self.host + '/rest/3.0/' + self._product_name + '/' + self._resource_name
        http_method = 'POST'
        opt[self.sign] = self._genSign(http_method, url, opt)

        headers = dict()
        headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=utf-8'
        headers['User-Agent'] = 'BCCS_SDK/3.0' +\
                                self.system_info +\
                                'python/2.7.3 (Baidu Push Server SDK V3.0.0) cli/Unknown'

        r = requests.request(http_method, url,
                             data=urllib.parse.urlencode(opt),
                             headers=headers
                             )

        return ResponseCore(r.headers, r.content, r.status_code)

    def _commonProcess(self, paramOpt):
        """返回结果处理"""

        ret = self._baseControl(paramOpt)
        if(ret is None):
            raise ChannelException('base control returned None object',
                                   self.channel_sdk_running_error)
        if ret.isOK():
            result = json.loads(ret.body)
            if (result is None):
                raise ChannelException(ret.body,
                                       self.channel_sdk_http_status_ok_but_result_error)
            self.request_id = result['request_id']
            if 'response_params' not in result:
                return None
            else:
                return self._byteify(result['response_params'])
        result = json.loads(ret.body)
        if(result is None):
            raise ChannelException('ret body:' + ret.body,
                                   self.channel_sdk_http_status_error_and_result_error)
        self.request_id = result['request_id']
        raise ChannelException(result['error_msg'], result['error_code'])

    def _checkConf(self):
        self.request_id = None

    def _byteify(self, input):
        if isinstance(input, dict):
            return {self._byteify(key): self._byteify(value) for key, value in input.items()}
        elif isinstance(input, list):
            return [self._byteify(element) for element in input]
        elif isinstance(input, str):
            return input.encode('utf-8')
        else:
            return input
