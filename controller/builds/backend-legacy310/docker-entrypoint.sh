#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/bash /etc/banner.sh
fi

DEVID=$(id -u ${APIUSER})
if [[ "${DEVID}" != "${CURRENT_UID}" ]]; then
    echo "Fixing uid of user ${APIUSER} from ${DEVID} to ${CURRENT_UID}..."
    usermod -u ${CURRENT_UID} ${APIUSER}
fi

GROUPID=$(id -g ${APIUSER})
if [[ "${GROUPID}" != "${CURRENT_GID}" ]]; then
    echo "Fixing gid user ${APIUSER} from ${GROUPID} to ${CURRENT_GID}..."
    groupmod -og ${CURRENT_GID} ${APIUSER}
fi

if [[ -z APP_MODE ]]; then
    APP_MODE="development"
fi

chown -R ${APIUSER} ${APP_SECRETS}
chmod u+w ${APP_SECRETS}

init_file="${APP_SECRETS}/initialized"
if [[ ! -f "${init_file}" ]]; then
    echo "Init flask app"
    HOME=${CODE_DIR} su -p ${APIUSER} -c 'restapi init --wait'
    if [[ "$?" == "0" ]]; then
        # Sync after init with compose call from outside
        touch ${init_file}
    else
        echo "Failed to startup flask!"
        exit 1
    fi
fi

# fix permissions on the main development folder
# chown ${APIUSER} ${CODE_DIR}

if [[ -d "${CERTDIR}" ]]; then
    chown -R ${APIUSER} ${CERTDIR}
fi

if [[ "${CRONTAB_ENABLE}" == "1" ]]; then
    if [[ "$(find /etc/cron.rapydo/ -name '*.cron')" ]]; then
        echo "Enabling cron..."

        # sed is needed to add quotes to env values and to escape quotes ( ' -> \\' )
        env | sed "s/'/\\'/" | sed "s/=\(.*\)/='\1'/" > /etc/rapydo-environment

        touch /var/log/cron.log
        chown ${APIUSER} /var/log/cron.log
        # Adding an empty line to cron log
        echo "" >> /var/log/cron.log
        cron
        # .cron extension is to avoid accidentally including backup files from editors
        cat /etc/cron.rapydo/*.cron | crontab -u ${APIUSER} -
        crontab -u ${APIUSER} -l
        echo "Cron enabled"
        # -n 1 will only print the empty line previously added
        tail -n 1 -f /var/log/cron.log &
    else
        echo "Found no cronjob to be enabled, skipping crontab setup"
    fi
fi

if [[ "$1" != 'rest' ]]; then
    ##CUSTOM COMMAND
    echo "Requested custom command:"
    echo "\$ $@"
    $@
else
    ##NORMAL MODES
    echo "REST API backend server is ready to be launched"

    if [[ ${ALEMBIC_AUTO_MIGRATE} == "1" ]] && [[ ${AUTH_SERVICE} == "sqlalchemy" ]]; then

        if [[ ! -d "${PROJECT_NAME}/migrations" ]]; then
            echo "Skipping migrations check, ${PROJECT_NAME}/migrations does not exist";
        elif [[ $(HOME=$CODE_DIR su -p ${APIUSER} -c 'alembic current 2>&1 | tail -1 | grep "head"') ]]; then
            echo "All database migrations are already installed";
        else
            HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi wait'

            # Please note that errors in the upgrade will not make fail the server startup due to the || true statement
            HOME=$CODE_DIR su -p ${APIUSER} -c 'alembic current || true';
            HOME=$CODE_DIR su -p ${APIUSER} -c 'alembic upgrade head || true';

            echo "Migration completed";
        fi

    fi

    if [[ "${APP_MODE}" == 'production' ]]; then

        echo "Waiting for services"
        HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi wait'

        echo "Ready to launch production gunicorn"
        mygunicorn

    elif [[ "$APP_MODE" == 'test' ]]; then

        echo "Testing mode"

        if [[ "${API_AUTOSTART}" == "1" ]]; then
            HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi wait'
            HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi launch'
        fi

    else
        echo "Development mode"

        if [[ "${API_AUTOSTART}" == "1" ]]; then
            HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi wait'
            HOME=$CODE_DIR su -p ${APIUSER} -c 'restapi launch'
        fi

    fi

    sleep infinity
fi
