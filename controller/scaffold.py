# -*- coding: utf-8 -*-

from utilities import template


def justatest(file='test.py'):
    data = {
        'name': "PEPPE!",
        # "date": "June 12, 2014",
        # "items": ["oranges", "bananas", "steak", "milk"]
    }
    return template.render(file, 'templates', **data)
