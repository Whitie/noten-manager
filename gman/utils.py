# -*- coding: utf-8 -*-

from io import BytesIO
from PIL import Image


MAX_SIZE = (200, 200)


def make_image(path):
    im = Image.open(path)
    im.thumbnail(MAX_SIZE)
    buffered = BytesIO()
    im.save(buffered, format='PNG')
    return buffered.getvalue()
