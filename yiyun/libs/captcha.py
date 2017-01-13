#!/usr/bin/env python

import os
import random
import string

from wheezy.captcha.image import captcha

from wheezy.captcha.image import background
from wheezy.captcha.image import curve
from wheezy.captcha.image import noise
from wheezy.captcha.image import smooth
from wheezy.captcha.image import text

from wheezy.captcha.image import offset
from wheezy.captcha.image import rotate
from wheezy.captcha.image import warp


__all__ = ['create_captcha']


def create_captcha():

    captcha_image = captcha(drawings=[
        background(),
        text(fonts=[
            os.path.join(
                os.path.abspath(os.path.dirname(__file__))) + '/fonts/Georgia.ttf',
            os.path.join(os.path.abspath(os.path.dirname(__file__))) + '/fonts/FreeSans.ttf'],
            drawings=[
                warp(),
                rotate(),
                offset()
        ]),
        curve(),
        noise(),
        smooth()
    ])

    chars = random.sample(string.ascii_letters + string.digits, 4)
    return captcha_image(chars), chars
