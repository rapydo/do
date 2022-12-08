#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/ash /etc/banner.sh
fi

PROXY_USER="nginx"

DEVID=$(id -u "$PROXY_USER")
if [ "$DEVID" != "$CURRENT_UID" ]; then
    echo "Fixing uid of user ${PROXY_USER} from $DEVID to $CURRENT_UID..."
    usermod -u "$CURRENT_UID" "$PROXY_USER"
fi

GROUPID=$(id -g $PROXY_USER)
if [ "$GROUPID" != "$CURRENT_GID" ]; then
    echo "Fixing gid of user $PROXY_USER from $GROUPID to $CURRENT_GID..."
    groupmod -og "$CURRENT_GID" "$PROXY_USER"
fi

echo "Running as ${PROXY_USER} (uid $(id -u ${PROXY_USER}))"

TEMPLATE_DIR="/etc/nginx/sites-enabled-templates"
CONF_DIR="/etc/nginx/sites-enabled"

mkdir -p ${CONF_DIR}
cp ${TEMPLATE_DIR}/maintenance.conf ${CONF_DIR}/

echo -e "\n\n"
echo "Maintenance server is up and waiting for connections. This server inform users that there is an ongoing maintenance"
echo "You can turn off this server after the maintenance is completed and before starting the normal stack"
echo -e "\n\n"

exec nginx -g 'daemon off;'
