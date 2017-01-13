import logging
import json
from random import randint, choice

from faker import Faker
import tornado.web
import tornado.ioloop
import tornado.httpserver
from tornado.httpclient import HTTPClient
from tornado.web import url
from tornado.options import options, define, parse_command_line


define("port", default=8090, type=int, help="listening port")


def fake_user_generator(uid):
    info = {"nickName": "nickName" + uid,
            "ptToken": "3VNO9f3kzj2CIb8MV4o1wQ==",
            "userHeadPicUrl": "http://example.com/headurl/" + uid,
            "userId": int(uid),
            "gender": 0,
            "birthday": 1317091800,
            "mobile": "18600896543"
            }
    return info


class GetUserInfoByToken(tornado.web.RequestHandler):

    def post(self):
        token = json.loads(self.request.body.decode())["ptToken"]
        info = fake_user_generator("183")
        data = {"code": 200, "message": "成功",
                "attribute": {"userInfo": info}}
        self.write(data)


class GetUserInfoByUserids(tornado.web.RequestHandler):

    def post(self):
        user_ids = json.loads(self.request.body.decode())["userIds"].split(",")
        users = []
        for uid in user_ids:
            users.append(fake_user_generator(uid))

        data = {
            "code": 200,
            "message": "成功",
            "attribute": {"userInfoList": users}
        }
        self.write(data)


class RefundHandler(tornado.web.RequestHandler):

    def post(self):
        fail_rtn = {1001: "订单生成失败", 1002: "退款失败",
                    1003: "没有该订单", 1004: "申请退款人与支付人不一致"}

        data = {"code": 200, "message": "成功"}
        if randint(1, 10) == 10:
            key = choice(list(fail_rtn.keys()))
            data = {"code": key, "message": fail_rtn[key]}

        body = json.loads(self.request.body.decode())
        notify_url = body.get("notifyUrl", None)
        logging.info("退款回调地址: {0}".format(notify_url))

        self.write(data)
        self.finish()

        if notify_url:

            notify_data = {"code": 200, "message": "成功",
                           "attribute": {"orderNo": body["orderNo"],
                                         "refundFee": body["refundTotalFee"]},
                           }
            client = HTTPClient()
            client.fetch(notify_url, method="POST",
                         body=json.dumps(notify_data))


class CreateOrderHandler(tornado.web.RequestHandler):

    def post(self):
        body = json.loads(self.request.body.decode())
        notify_url = body["notifyUrl"]
        logging.info("新建订单回调地址: {0}".format(notify_url))

        faker = Faker()
        order_no = faker.pystr()

        data = {"code": 200, "message": "成功",
                "attribute": {"orderNo": order_no}}
        self.write(data)
        self.finish()

        client = HTTPClient()

        logging.info("开始回调异步支付通知...")
        notify_body = {"message": "成功", "code": 200,
                       "attribute": {"userId": 169,
                                     "orderNo": order_no,
                                     "paymentMethod": 1,
                                     "orderState": 2}}
        client.fetch(notify_url, method="POST", body=json.dumps(notify_body))


class MatchPushHandler(tornado.web.RequestHandler):

    def post(self):
        body = json.loads(self.request.body.decode())
        logging.info("获取到请求正文: {0}".format(body))
        data = {"code": 200, "message": "成功"}
        self.write(data)


def main():
    handlers = (
        url(r"/match/openapi/getUserInfoList.do", GetUserInfoByUserids),
        url(r"/match/openapi/getUserInfo.do", GetUserInfoByToken),
        url(r"/match/openapi/applyRefundOrder.do", RefundHandler),
        url(r"/match/openapi/createOrderInfo.do", CreateOrderHandler),
        url(r"/match/openapi/matchPush.do", MatchPushHandler),
    )

    app = tornado.web.Application(
        debug=True,
        handlers=handlers
    )

    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    loop = tornado.ioloop.IOLoop.instance()
    logging.info("Fake Parteam start at port: {0}".format(options.port))
    http_server.listen(port=options.port)
    loop.start()


if __name__ == '__main__':
    parse_command_line()
    main()
