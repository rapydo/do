#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/bash /etc/banner.sh
fi

if [[ "${APP_MODE}" == "test" ]]; then
    APP_MODE="development"
fi

cp /etc/nginx/adminer-${APP_MODE}.conf /etc/nginx/sites-enabled/adminer.conf

nginx

echo "NGINX started"
