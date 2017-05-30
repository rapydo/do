# -*- coding: utf-8 -*-

"""
Convert README file from Markdown to text
"""

from bs4 import BeautifulSoup
from markdown import markdown

empty = ''
file = 'README.md'

with open(file, 'r') as rhandler:
    mdcontent = rhandler.read()

    text = empty.join(
        BeautifulSoup(
            markdown(mdcontent), "html5lib"
        ).findAll(text=True)
    )

    with open(file.split('.')[0], 'w') as whandler:
        whandler.write(text)
