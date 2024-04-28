#!/bin/bash
set -e

REDIS_USER="redis"

DEVID=$(id -u "${REDIS_USER}")
if [ "${DEVID}" != "${CURRENT_UID}" ]; then
    echo "Fixing uid of user ${REDIS_USER} from ${DEVID} to ${CURRENT_UID}..."
    usermod -u "$CURRENT_UID" "${REDIS_USER}"
fi

GROUPID=$(id -g ${REDIS_USER})
if [ "${GROUPID}" != "${CURRENT_GID}" ]; then
    echo "Fixing gid of user ${REDIS_USER} from ${GROUPID} to ${CURRENT_GID}..."
    groupmod -og "${CURRENT_GID}" "${REDIS_USER}"
fi
