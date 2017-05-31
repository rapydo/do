# -*- coding: utf-8 -*-

"""
Handling IDs in a more secure way
"""

import uuid


def getUUID():
    return str(uuid.uuid4())


def getUUIDfromString(string):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, string))
