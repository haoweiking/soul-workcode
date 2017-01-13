

import qiniu
import base64
from qiniu import PersistentFop, op_save
from qiniu import BucketManager
from yiyun.core import celery, current_app


def get_quniu_auth():
    access_key = current_app.settings['qiniu_access_key']
    secret_key = current_app.settings['qiniu_secret_key']

    return qiniu.Auth(access_key, secret_key)


def get_upload_token(bucket_name, key=None, policy=None):
    q = get_quniu_auth()
    return q.upload_token(bucket_name, key=key, policy=policy)


def put_data(bucket_name, key, data, mime_type="application/octet-stream", check_crc=True):
    token = get_upload_token(bucket_name, key)
    ret, info = qiniu.put_data(
        token, key, data, mime_type=mime_type, check_crc=check_crc)

    return ret, info


@celery.task
def put_file(bucket_name, key, localfile, mime_type="application/octet-stream", check_crc=True):
    token = get_upload_token(bucket_name, key)
    ret, info = qiniu.put_file(
        token, key, localfile, mime_type=mime_type, check_crc=check_crc)

    return ret, info


@celery.task
def delete_file(bucket_name, key):
    q = get_quniu_auth()
    bucket = qiniu.BucketManager(q)

    ops = qiniu.build_batch_delete(bucket_name, [key])

    ret, info = bucket.batch(ops)
    return ret, info
