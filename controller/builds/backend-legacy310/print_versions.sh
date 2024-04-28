#!/bin/bash

# even if !/bin/bash, it will be executed as /bin/sh, do not use [[ ... ]]
if [ ${HOSTNAME} = "backend-server" ]; then
    echo "$(python3 --version) - $(flask --version | grep Flask)"
elif [ ${HOSTNAME} = "flower" ]; then
    echo "$(python3 --version) - Celery $(celery --version) - Flower $(pip3 list | grep flower | awk {'print $2'})"
else
    echo "$(python3 --version) - Celery $(celery --version)"
fi