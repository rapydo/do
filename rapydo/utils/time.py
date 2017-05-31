# -*- coding: utf-8 -*-

import pytz
from datetime import datetime


def timestamp_from_string(timestamp_string):
    """
    Neomodels complains about UTC, this is to fix it.
    Taken from http://stackoverflow.com/a/21952077/2114395
    """

    precision = float(timestamp_string)
    # return datetime.fromtimestamp(precision)

    utc_dt = datetime.utcfromtimestamp(precision)
    aware_utc_dt = utc_dt.replace(tzinfo=pytz.utc)

    return aware_utc_dt
