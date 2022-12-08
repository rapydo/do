#!/bin/sh

set -e
set -o allexport

if [[ ! -t 0 ]]; then
    /bin/ash /etc/banner.sh
fi

if [[ "${APP_MODE}" == "test" ]]; then
    APP_MODE="development"
fi

# We pass to envsubst the list of env variables, to only replace existing variables
envsubst "$(env | cut -d= -f1 | sed -e 's/^/$/')" < /etc/nginx/swaggerui-${APP_MODE}.conf > /etc/nginx/nginx.conf

if [[ ${APP_MODE} == "production" ]];
then
    export URLS="[ { url: 'https://${DOMAIN}/api/specs', name: '${PROJECT_TITLE}' } ]"
else
    export URLS="[ { url: 'http://${DOMAIN}:${BACKEND_PORT}/api/specs', name: '${PROJECT_TITLE}' } ]"
fi
