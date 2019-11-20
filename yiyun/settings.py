import os
from celery.schedules import timedelta, crontab

DEBUG = False

# 接口关闭
API_CLOSED = False

COOKIE_SECRET = 'yiyun'
SECRET_KEY = 'yiyun'
XSRF_COOKIES = False
SESSION_EXPIRES = 31536000

# default templates and static path settings
BASEDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)))
TEMPLATE_PATH = os.path.join(BASEDIR, 'templates')
STATIC_PATH = os.path.join(BASEDIR, 'static')
UPLOAD_PATH = os.path.join(os.path.dirname(BASEDIR), 'upload')

# mysql server config
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_PORT = 3306
DB_USER = os.environ.get("MYSQL_USER", "root")
DB_PASSWD = os.environ.get("MYSQL_PASSWORD", "")
DB_NAME = os.environ.get("MYSQL_DATABASE", "yiyun")
DB_MAX_CONNS = os.environ.get("MYSQL_MAX_CONNS", 30)

# redis connection config
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = 6379

REDIS_URL = 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT)
CELERY_BROKER_URL = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_URL = 'redis://%s:%s/2' % (REDIS_HOST, REDIS_PORT)

MAIL_SERVER = "127.0.0.1"
MAIL_SERVER_PORT = 25
MAIL_USER = ""
MAIL_PASS = ""
MAIL_SENDER = ""

SENDCLOUD_USER = ""
SENDCLOUD_KEY = ""
SENDCLOUD_SENDER = ""

SENTRY_DSN = ''

# 云通讯接口
CLOOPEN_ACCOUNT = ""
CLOOPEN_AUTH_TOKEN = ""
CLOOPEN_APPID = ""
CLOOPEN_TEMPLATEID = ""
CLOOPEN_IS_SANDBOX = True

# 支付宝接口配置
ALIPAY_PARTNER = ''
ALIPAY_SELLER_EMAIL = ''
ALIPAY_SIGN_TYPE = 'RSA'
ALIPAY_KEY = ''
ALIPAY_PUBLIC_KEY = ''
ALIPAY_PRIVATE_KEY = ''

# 七牛存储
QINIU_ACCESS_KEY = ""
QINIU_SECRET_KEY = ""

QINIU_AVATAR_BUCKET = ""
QINIU_FILE_BUCKET = ""

# 微信开放平台
WEIXIN_APPID = ''
WEIXIN_APPSECRET = ''

# weixin 网站登录
WEIXIN_WEB_APPID = ""
WEIXIN_WEB_APPSECRET = ""

# 新浪微博接口
WEIBO_APIKEY = ""
WEIBO_APISECRET = ""

# QQ互联接口
QQ_IOS_APIID = ""
QQ_IOS_APIKEY = ""

QQ_ANDROID_APIID = ""
QQ_ANDROID_APIKEY = ""

QQ_WEB_APIID = ""
QQ_WEB_APIKEY = ""

# urls settings
AVATAR_URL = "" # 对应 QINIU_AVATAR_BUCKET
ATTACH_URL = "" # 对应 QINIU_FILE_BUCKET
CANONICAL_URL_PREFIX = "" 
STATIC_URL_PREFIX = "/static/"

# 网易云信接口
NETEASEIM_APPKEY = ""
NETEASEIM_APPSECRET = ""

# 微信支付
WXPAY_APPID = ""
WXPAY_MCHID = ""
WXPAY_SECRET_KEY = ""

"""
微信支付的退款证书

WXPAY_CA_CERTS: CA 证书路径, (rootca.pem)
WXPAY_API_CLIENT_CERT: 证书私钥路径 (apiclient_cert.pem)
WXPAY_API_CLIENT_KEY: 证书密钥路径 (apiclient_key.pem)
"""
WXPAY_CA_CERTS = None
WXPAY_API_CLIENT_CERT = None
WXPAY_API_CLIENT_KEY = None


# 微信第三方平台
WX_COMP_APPID = ""
WX_COMP_APPSECRET = ""
WX_COMP_TOKEN = ""
WX_COMP_AES_KEY = ""

# 高德地图
AMAP_REST_KEY = ""
AMAP_REST_SECRET = ""
AMAP_JS_KEY = ""

CLUB_URL = ""
MAIN_URL = ""

# paidui接口服务器
PARTEAM_API_URL = ""
PARTEAM_AVATAR_BASE_URL = ""

# celery 定时任务
CELERYBEAT_SCHEDULE = {
    "schedule_scan_match_start_time": {
        "task": "yiyun.tasks.match_notify.scan_match_start_time",
        "schedule": crontab(minute="*/10")
    },
}
