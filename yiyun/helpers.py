import os
import sys
import re
import random
import string
import time
import json
import uuid

import socket
import struct

from Crypto.Cipher import AES
from Crypto import Random
from base64 import b64encode, b64decode

from dateutil.tz import gettz, tzutc
from datetime import datetime, date
from decimal import Decimal

from geopy import distance as geopy_distance

from yiyun.libs.pinyin import Pinyin

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
_pre_re = re.compile(
    r'<pre (?=lang=[\'"]?\w+[\'"]?).*?>(?P<code>[\w\W]+?)</pre>')
_lang_re = re.compile(r'lang=[\'"]?(?P<lang>\w+)[\'"]?')


class Storage(dict):

    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    >>> o = storage(a=1)
    >>> o.a
    1
    >>> o['a']
    1
    >>> o.a = 2
    >>> o['a']
    2
    >>> del o.a
    >>> o.a
    Traceback (most recent call last):
    ...
    AttributeError: 'a'
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as k:

            raise AttributeError(k)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage


class JSONEncoder(json.JSONEncoder):

    """The default Flask JSON encoder.  This one extends the default simplejson
    encoder by also supporting ``datetime`` objects, ``UUID`` as well as
    ``Markup`` objects which are serialized as RFC 822 datetime strings (same
    as the HTTP date format).  In order to support more data types override the
    :meth:`default` method.
    """

    def default(self, o):
        """Implement this method in a subclass such that it returns a
        serializable object for ``o``, or calls the base implementation (to
        raise a :exc:`TypeError`).
        For example, to support arbitrary iterators, you could implement
        default like this::
            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(o, date):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, bytes):
            return o.decode("utf-8")
        if hasattr(o, '__html__'):
            return o.__html__()
        if not o:
            return ""

        return json.JSONEncoder.default(self, o)


def load_class(s):
    path, klass = s.rsplit('.', 1)
    __import__(path)
    mod = sys.modules[path]
    return getattr(mod, klass)


def find_subclasses(klass, include_self=False):
    accum = []
    for child in klass.__subclasses__():
        accum.extend(find_subclasses(child, True))
    if include_self:
        accum.append(klass)
    return accum


def setting_from_object(obj):
    settings = dict()
    for key in dir(obj):
        if key.isupper():
            settings[key.lower()] = getattr(obj, key)

    return settings


class ObjectDict(dict):

    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None

    def __setattr__(self, key, value):
        self[key] = value


class cached_property(object):

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, None)
        if value is None:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def slugify(text, delim='-'):
    """Generates an ASCII-only slug. From http://flask.pocoo.org/snippets/5/"""
    result = []
    for word in _punct_re.split(text.lower()):
        # word = word.encode('translit/long')
        if word:
            result.append(word)
    return str(delim.join(result))


def humansize(nbytes):

    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def generate_random(length=8):
    """Generate random number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def create_token(length=16):
    chars = list(string.ascii_letters + string.digits)
    salt = ''.join([random.choice(chars) for i in range(length)])
    return salt


def random_string(length=16):
    salt = ''.join([random.choice(list(string.ascii_letters + string.digits + "_")) for i in range(length)])
    return salt


def random_hexstring(n):
    rnd_bytes = [str(hex(random.randint(0, 255)))[2:] for i in range(n)]
    return "".join(["0%s" % b if len(b) == 1 else b for b in rnd_bytes]).upper()


def intval(value):

    try:
        return int(float(value))
    except:
        pass

    return 0


def floatval(value):

    try:
        return float(value)
    except:
        pass

    return 0.00


def decimalval(value, places=2):
    try:
        return Decimal(value).quantize(Decimal('.1') ** places)
    except:
        pass

    return Decimal("0.0")


def nl2br(content):
    return content.replace("\n", '<br />')


def utctime():
    epoch = datetime(1970, 1, 1, 0, 0, 0)
    return (datetime.utcnow() - epoch).total_seconds()


def utc_to_local(utc_datetime, to_tz=None):

    if not utc_datetime:
        return None

    if not to_tz:
        to_tz = 'Asia/Shanghai'

    return utc_datetime.replace(tzinfo=tzutc()).astimezone(gettz(to_tz))


def geocode_distance(xxx_todo_changeme, xxx_todo_changeme1, unit='km'):

    (x1, y1) = xxx_todo_changeme
    (x2, y2) = xxx_todo_changeme1
    if (x1, y1) == (x2, y2):
        return 0

    d = geopy_distance.distance((x1, y1), (x2, y2))
    if unit == 'miles':
        return d.miles
    else:
        return d.kilometers


def date_to_str(obj, format="%Y-%m-%dT%H:%M:%S+08:00"):
    return datetime.strftime(obj, format)


def format_distance(distance):

    if distance > 1000:
        return "{:,d}公里".format(int(distance / 1000))

    return "{:,d}米".format(int(distance))


def format_duration(duration):

    if duration < 60:
        return "%d秒" % duration
    elif duration < 3600:
        return "%d分钟" % int(duration / 60)

    elif duration % 3600 > 0:
        return "%s小时%d分钟" % ("{:,d}".format(int(duration / 3600)), int((duration % 3600) / 60))

    else:
        return "%d小时" % int(duration / 3600)


def human_duration(seconds):
    return "%s'%s" % (seconds // 60, seconds % 60)


def is_lat(value):
    value = abs(floatval(value))
    return value > 0 and value <= 90


def is_lng(value):
    value = abs(floatval(value))
    return value > 0 and abs(floatval(value)) <= 180


def baseN(num, b):
    return ((num == 0) and "0") or (baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyz"[num % b])


def is_mobile(value):
    return re.match(r"^(13[0-9]|15[012356789]|17[0678]|18[0-9]|14[57])[0-9]{8}$", value) is not None


def is_email(value):
    return re.match(r"^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", value) is not None


def ip2long(ipstr):
    struct.unpack("!I", socket.inet_aton(ipstr))[0]


def long2ip(ip):
    return socket.inet_ntoa(struct.pack('!L', ip))


def chunks(arr, n):
    """将指定数组分成 m 份，每份 n 个元素"""
    return [arr[i:i + n] for i in range(0, len(arr), n)]


def datetime_from_string(time_string, format="%Y-%m-%d %H:%M:%S"):
    """将时间字符串转换成datetime 对象"""

    # assert (isinstance(time_string, (str, unicode)), "time_string: %s" % time_string)

    if time_string:
        return datetime.fromtimestamp(time.mktime(time.strptime(time_string, format)))

    else:
        return None


def get_mp3_info(audio_file):

    fp = os.popen(
        "ffprobe -v quiet -print_format json -show_format -show_streams %s" % audio_file)
    data = fp.read()
    fp.close()

    mp3_info = json.loads(data)

    return mp3_info


def aes_encrypt(plain_text, secret_key):

    if not secret_key:
        return plain_text

    plain_text += (16 - len(plain_text) % 16) * "\0"
    iv = Random.new().read(AES.block_size)

    encryption_suite = AES.new(secret_key, AES.MODE_CBC, iv)
    cipher_text = encryption_suite.encrypt(plain_text)
    return b64encode(iv + cipher_text)


def aes_decrypt(cipher_text, secret_key):
    if not secret_key:
        return cipher_text

    cipher_text = b64decode(cipher_text)
    decryption_suite = AES.new(
        secret_key, AES.MODE_CBC, cipher_text[:AES.block_size])
    plain_text = decryption_suite.decrypt(cipher_text[AES.block_size:])

    return plain_text.rstrip("\0")


def to_pinyin(name, spliter=""):

    def clean(name):
        delcstr = '《》〈 〉（）&%￥#@！{}【】、，。……“”「」『』‘’●；：──·~・•'

        for char in delcstr:
            name = name.replace(char, " ")

        name = name.strip()
        name = re.sub(r"\d+", " \g<0> ", name)
        name = re.sub(r"[a-zA-Z]+", " \g<0> ", name)

        _punct_re = re.compile(r'[\t!"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')
        name = _punct_re.sub(" ", name)

        return name

    name = clean(name)
    parts = [n for n in name.strip().split(" ") if n.strip()]

    pinyin = ""
    for part in parts:
        if re.match(r"^[0-9]+$", part):
            pinyin += part
        elif re.match(r"^[0-9a-zA-Z]+$", part):
            pinyin += part
        else:
            pinyin += Pinyin.t(part, spliter)

        pinyin += spliter

    return pinyin.rstrip(",").lower()


def to_jianpin(name):

    pinyin = to_pinyin(name, ",")
    parts = pinyin.split(",")

    jianpin = ""
    for part in parts:
        if not part:
            continue

        if re.match(r"^[0-9]+$", part):
            jianpin += part
        else:
            jianpin += part[0]

    return jianpin.lower()


def merge_dict(dict1, dict2):
    dict1.update(dict2)
    return dict1
