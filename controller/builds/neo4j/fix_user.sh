#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/bash /etc/banner.sh
fi

NEO4J_USER="neo4j"

DEVID=$(id -u "$NEO4J_USER")
if [ "$DEVID" != "$CURRENT_UID" ]; then
    echo "Fixing uid of user ${NEO4J_USER} from $DEVID to $CURRENT_UID..."
    usermod -u "$CURRENT_UID" "$NEO4J_USER"
fi

GROUPID=$(id -g $NEO4J_USER)
if [ "$GROUPID" != "$CURRENT_GID" ]; then
    echo "Fixing gid of user $NEO4J_USER from $GROUPID to $CURRENT_GID..."
    groupmod -og "$CURRENT_GID" "$NEO4J_USER"
fi
