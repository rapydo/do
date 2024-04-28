#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/ash /etc/banner.sh
fi

POSTGRES_USER="postgres"

DEVID=$(id -u ${POSTGRES_USER})
if [[ "${DEVID}" != "${CURRENT_UID}" ]]; then
    echo "Fixing uid of user ${POSTGRES_USER} from ${DEVID} to ${CURRENT_UID}..."
    usermod -u ${CURRENT_UID} ${POSTGRES_USER}
fi

GROUPID=$(id -g ${POSTGRES_USER})
if [[ "${GROUPID}" != "${CURRENT_GID}" ]]; then
    echo "Fixing gid user ${POSTGRES_USER} from ${GROUPID} to ${CURRENT_GID}..."
    groupmod -og ${CURRENT_GID} ${POSTGRES_USER}
fi

DATADIR="$(dirname $PGDATA)/${PG_MAJOR}"
# Create the version datadir, if missing
mkdir -p ${DATADIR}

chown -R ${POSTGRES_USER} ${DATADIR}

# Create current link, if missing
if [[ ! -L $PGDATA ]]; then
    ln -sT ${DATADIR} ${PGDATA};
fi

if [[ -f ${PGDATA}/postgresql.conf ]] && [[ ! -L ${PGDATA}/postgresql.conf ]]; then
    # Force postgresql.conf in datadir to be a link to the default conf file
    # Default conf file is copied into the container at build time
    # This will update alredy-created datadirs.
    # A similar check in pgs_init.sh will ensure the link for newly created datadirs
    ln -sf /etc/postgresql/postgresql.conf ${PGDATA}/postgresql.conf
fi