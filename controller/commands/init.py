# -*- coding: utf-8 -*-
import os
from controller import DATA_FOLDER, LOGS_FOLDER
from controller import log


def __call__(**kwargs):

    if not os.path.exists(DATA_FOLDER):
        log.info("Data folder not found, created it", LOGS_FOLDER)
        # this will create both data and data/logs
        os.makedirs(LOGS_FOLDER)

    elif not os.path.exists(LOGS_FOLDER):
        log.info("Logs folder ({}) not found, created it", LOGS_FOLDER)
        os.makedirs(LOGS_FOLDER)

    log.info("Project initialized")
