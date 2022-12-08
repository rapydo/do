#!/bin/bash

HOME=${CODE_DIR} su -p ${APIUSER} -c "celery --app restapi.connectors.celery.worker.celery_app inspect ping -t 5 -d celery@${PROJECT_NAME}-${HOSTNAME}"

