# coding: utf-8

import json
import logging

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from celery import current_app as app

from yiyun.core import celery
from yiyun.libs import cloopen
from yiyun.libs.baidu_push import Channel


@celery.task
def send_sms_verifycode(to, verifycode, expire_in="30", template_id=None):

    account_sid = app.settings["cloopen_account"]
    auth_token = app.settings["cloopen_auth_token"]
    app_id = app.settings["cloopen_appid"]
    is_sandbox = app.settings["cloopen_is_sandbox"]

    if template_id is None:
        template_id = app.settings["cloopen_templateid"]

    client = cloopen.Cloopen(account_sid=account_sid, auth_token=auth_token,
                             app_id=app_id, is_sandbox=is_sandbox)

    datas = [str(verifycode), str(expire_in)]

    return client.send_tpl_sms(to, template_id, datas)


@celery.task
def send_email(to_email, subject, html):

    sendcloud_user = app.settings.get("sendcloud_user", None)
    if sendcloud_user:
        return sendcloud_mail(to_email, subject, html)

    mail_server = app.settings["mail_server"]
    assert mail_server
    mail_server_port = app.settings["mail_server_port"]

    mail_user = app.settings["mail_user"]
    mail_pass = app.settings["mail_pass"]

    from_email = app.settings["mail_sender"]

    if not isinstance(to_email, list):
        to_email = [to_email, ]

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_email)

    part = MIMEText(html, 'html', 'utf-8')
    msg.attach(part)

    s = smtplib.SMTP(mail_server, mail_server_port)

    if mail_user and mail_pass:
        s.login(mail_user, mail_pass)

    s.sendmail(from_email, to_email, msg.as_string())
    s.quit()


@celery.task
def sendcloud_mail(to_email, subject, html):

    url = "http://api.sendcloud.net/apiv2/mail/send"

    sendcloud_user = app.settings.get("sendcloud_user")
    sendcloud_key = app.settings.get("sendcloud_key")
    from_email = app.settings.get("sendcloud_sender")

    # 不同于登录SendCloud站点的帐号，您需要登录后台创建发信子帐号，使用子帐号和密码才可以进行邮件的发送。
    params = {"apiUser": sendcloud_user,
              "apiKey": sendcloud_key,
              "to": to_email,
              "from": from_email,
              "fromname": "",
              "subject": subject,
              "html": html
              }

    r = requests.post(url, data=params)

    if r.status_code != 200:
        logging.error("sendcloud failed: %s" % r.text)

    resp = r.json()
    if resp['statusCode'] != 200:
        logging.error("sendcloud failed: %s" % resp)


@celery.task
def sendcloud_template_mail(to_email, subject, template_name, sub={}):

    url = "http://api.sendcloud.net/apiv2/mail/sendtemplate"

    sendcloud_user = app.settings.get("sendcloud_user")
    sendcloud_key = app.settings.get("sendcloud_key")
    from_email = app.settings.get("sendcloud_sender")

    xsmtpapi = {
        "to": [to_email],
        "sub": sub
    }

    r = requests.post(url,
                      data={"apiUser": sendcloud_user,
                            "apiKey": sendcloud_key,
                            "templateInvokeName": template_name,
                            "to": to_email,
                            "from": from_email,
                            "fromname": from_email,
                            "subject": subject,
                            "xsmtpapi": json.dumps(xsmtpapi)
                            })

    resp = r.json()
    if resp['statusCode'] != 200:
        logging.error("sendcloud(tpl) failed: %s" % resp)


@celery.task
def push_message(user_id, content, title="", data=None):

    def _build_android_notification(title, content, data=None):
        msg = {
            "title": title,
            "description": content
        }

        if data is not None:
            msg['custom_content'] = data

        return json.dumps(msg)

    def _build_ios_notification(content, data=None, sound="", badge=0):
        msg = {
            "aps": {
                "alert": content,
                "sound": sound
            }
        }

        if badge > 0:
            msg['aps']['badge'] = badge

        if isinstance(data, dict):
            msg.update(data)

        return json.dumps(msg)

    ios = Channel(app.settings['bpush_ios_apikey'], app.settings['bpush_ios_secretkey'],
                  deviceType=Channel.DEVICE_TYPE_IOS)

    android = Channel(app.settings['bpush_android_apikey'], app.settings['bpush_android_secretkey'],
                      deviceType=Channel.DEVICE_TYPE_ANDROID)

    if user_id == 'all':
        ios.pushMsgToAll(_build_ios_notification(content, data),
                         opts={
                         "deploy_status": app.settings['bpush_ios_deploy_status'],
                         "msg_type": 1
                         })
        android.pushMsgToAll(_build_android_notification(title, content, data),
                             opts={"msg_type": 1})

    elif user_id == 'ios':
        ios.pushMsgToAll(_build_ios_notification(content, data),
                         opts={
                         "deploy_status": app.settings['bpush_ios_deploy_status'],
                         "msg_type": 1
                         })

    elif user_id == 'android':
        android.pushMsgToAll(_build_android_notification(title, content, data),
                             opts={"msg_type": 1})

    elif user_id:
        # user = User.get_or_none(id=user_id)
        device = Device.get_or_none(owner_id=user_id)

        if device and device.push_id:
            if device.device_type == "ios":
                ios.pushMsgToSingleDevice(device.push_id,
                                          _build_ios_notification(content, data, badge=1),
                                          opts={
                                              "deploy_status": app.settings['bpush_ios_deploy_status'],
                                              "msg_type": 1
                                          })
            else:
                android.pushMsgToSingleDevice(
                    device.push_id,
                    _build_android_notification(title, content, data),
                    opts={
                        "msg_type": 1
                    })
