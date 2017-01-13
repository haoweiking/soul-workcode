
import os
from base64 import urlsafe_b64decode
from io import BytesIO
import qrcode

from .base import WebBaseHandler, web_app
from yiyun.helpers import intval


@web_app.route("/")
class HomeHandler(WebBaseHandler):
    """docstring for HomeHandler"""

    def get(self):
        self.redirect(self.reverse_url("club_home"))


@web_app.route("/tool/qrcode/(.*)", name="generate_qrcode")
class GenerateQrCode(WebBaseHandler):
    """docstring for GenerateQrCode"""

    def get(self, key):

        content = urlsafe_b64decode(key)

        attname = self.get_argument("attname", "")
        size = intval(self.get_argument("size", 512))

        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=30,
            border=1,
        )
        qr.add_data(content)
        img = qr.make_image()

        if size > 1280:
            size = 1280

        elif size < 16:
            size = 16

        img.thumbnail((size, size))

        fp = BytesIO()
        img.save(fp)
        fp.seek(0, os.SEEK_END)

        if attname:
            self.set_header('Content-Description', 'File Transfer')
            self.set_header('Content-Disposition', 'attachment; filename=%s' % attname)
            self.set_header('Content-Transfer-Encoding', 'binary')

            self.set_header('Pragma', 'public')
            self.set_header('Content-Length', fp.tell())

        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
        self.set_header('Content-Type', 'image/png')

        self.write(fp.getvalue())
