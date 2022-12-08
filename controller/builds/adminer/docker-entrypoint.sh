#!/bin/sh

set -e

if [[ ! -t 0 ]]; then
    /bin/ash /etc/banner.sh
fi

if [[ "${APP_MODE}" == "test" ]]; then
    APP_MODE="development"
fi

cp /etc/nginx/adminer-${APP_MODE}.conf /etc/nginx/http.d/adminer.conf

nginx

echo "NGINX started"
