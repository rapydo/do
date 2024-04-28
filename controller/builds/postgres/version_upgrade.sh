#!/bin/bash
set -e

echo ""

PGFOLDER="/var/lib/postgresql"
DATAFOLDER="${PGFOLDER}/current"
BACKUPFOLDER="/backup/postgres"

error() {
    echo -e "\e[31m${1}\e[0m"
    exit 1
}
# env variable
if [[ $DATAFOLDER != $PGDATA ]]; then
    error "Env variable PGDATA is expected to be equal to ${DATAFOLDER} and not ${PGDATA}, cannot continue"
fi

if [[ -f $DATAFOLDER ]]; then
    error "Unexcepted ${DATAFOLDER} type, it is a file"
fi

if [[ ! -L $DATAFOLDER ]]; then
    error "Unexcepted ${DATAFOLDER} type, is it a folder? A link is expected"
fi

if [[ ! -f $DATAFOLDER/PG_VERSION ]]; then
    error "${DATAFOLDER}/PG_VERSION not found"
fi

CURRENT_VERSION=$(cat ${DATAFOLDER}/PG_VERSION)
if [[ -z "${CURRENT_VERSION##*[!0-9]*}" ]]; then
	error "Current version ${CURRENT_VERSION} is not a number"
fi

NEW_VERSION=$PG_MAJOR
if [[ -z "${NEW_VERSION##*[!0-9]*}" ]]; then
    error "New version ${NEW_VERSION} is not a number"
fi

if [[ ${CURRENT_VERSION} -eq ${NEW_VERSION} ]]; then
    error "Current version is already upgraded to version ${NEW_VERSION}"
fi

if [[ ${CURRENT_VERSION} -gt ${NEW_VERSION} ]]; then
    error "Current version (${CURRENT_VERSION}) is greater then new version (${NEW_VERSION}). Downgrade is not supported"
fi

# This is the case data is already a link to a version-aware folder
if [[ -L $DATAFOLDER ]]; then
    REAL_PATH=$(realpath $DATAFOLDER)
    if [[ $REAL_PATH != ${PGFOLDER}/${CURRENT_VERSION} ]]; then
    error cho "Data folder is expected to be a link to ${PGFOLDER}/${CURRENT_VERSION}, but ${REAL_PATH} is found"
    fi
fi

let NEXT_VERSION=CURRENT_VERSION+1
if [[ $NEXT_VERSION -lt ${NEW_VERSION} ]]; then
    echo "WARNING!"
    echo "You requested to upgrade from version ${CURRENT_VERSION} to version ${NEW_VERSION}"
    echo "It is always advisable to upgrade 1 major version at a time."
    echo ""
    echo "If you want to continue, ignore this warning."
    echo "Otherwise CTRL+C to interrupt the current operation"
    echo ""
    SLEEP=10
    echo "Sleeping ${SLEEP} seconds..."
    sleep $SLEEP
fi

echo -e "You requested to upgrade from version \e[32m${CURRENT_VERSION}\e[0m to version \e[32m${NEW_VERSION}\e[0m."
echo ""

if [[ ! -d ${PGFOLDER}/${NEW_VERSION} ]]; then
    echo "${PGFOLDER}/${NEW_VERSION} is missing, creating it..."
    mkdir -p ${PGFOLDER}/${NEW_VERSION}
    chown postgres ${PGFOLDER}/${NEW_VERSION}
fi

if [ ! -z "$(ls -A ${PGFOLDER}/${NEW_VERSION})" ]; then
    error "${PGFOLDER}/${NEW_VERSION} is not empty, cannot upgrade"
fi

if [[ -z $1 ]]; then

    echo "Please select one of the following backup files by executing:"
    echo ""
    echo -e "$ \e[32mversion_upgrade backupfile\e[0m"
    echo ""
    echo "If nothing is listed, please make a backup before starting this upgrade script"
    echo ""

    for BACKUP_NAME in $(ls ${BACKUPFOLDER}/*.sql.gz); do
        echo -e " - \e[32m$(basename $BACKUP_NAME)\e[0m $(stat -c '\tSize: %s' ${BACKUP_NAME})"
    done

    exit 1
else
    BACKUP_NAME=$1
    if [[ -f ${BACKUPFOLDER}/${BACKUP_NAME} ]]; then
        echo -e "You selected backup:\t\e[32m${BACKUP_NAME}\e[0m $(stat -c '\tSize: %s' ${BACKUPFOLDER}/${BACKUP_NAME})"
        echo ""
    else
        error "Backup file ${BACKUP_NAME} not found in ${BACKUPFOLDER}"
    fi
fi


if [[ ${BACKUP_NAME: -7} != ".sql.gz" ]]; then
    error "Invalid backup file, unexpected format! Backup files are expected to have .sql.gz extension"
fi

SLEEP_TIME=5
echo "##################################################################"
# Update the current link to the TO folder
echo -e "\e[32mUpdating the current link to the version ${NEW_VERSION} folder\e[0m"
echo ln -sfT ${PGFOLDER}/${NEW_VERSION} ${DATAFOLDER}
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
ln -sfT ${PGFOLDER}/${NEW_VERSION} ${DATAFOLDER}
echo ""

echo "##################################################################"
# Initialize the new database folder
echo -e "\e[32mInitializing the folder for version ${NEW_VERSION}\e[0m"
echo su - -c \"initdb -D ${DATAFOLDER}\" postgres
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
su - -c "initdb -D ${DATAFOLDER}" postgres
echo ""

echo "##################################################################"
# Restore previous configuration files
echo -e "\e[32mpg_hba.conf and postgresql.conf will be copied from version ${CURRENT_VERSION} to version ${NEW_VERSION}\e[0m"
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
# -d  Preserve symlinks
# -p  Preserve file attributes if possible
cp -dp ${PGFOLDER}/${CURRENT_VERSION}/pg_hba.conf ${PGFOLDER}/${NEW_VERSION}/pg_hba.conf
cp -dp ${PGFOLDER}/${CURRENT_VERSION}/postgresql.conf ${PGFOLDER}/${NEW_VERSION}/postgresql.conf
chown postgres ${PGFOLDER}/${NEW_VERSION}/pg_hba.conf ${PGFOLDER}/${NEW_VERSION}/postgresql.conf
echo ""

echo "##################################################################"
# Run postgres
echo -e "\e[32mPostgres server will be executed\e[0m"
echo su - -c \"postgres -D ${DATAFOLDER}\" postgres
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
su - -c "postgres -D ${DATAFOLDER}" postgres &
echo ""

echo ""
echo "Waiting postgres to start"
sleep 10
echo ""

echo "##################################################################"
# Restore the default user
echo -e "\e[32mRecreating the ${POSTGRES_USER} user\e[0m"
echo su - -c \"createuser -s ${POSTGRES_USER}\" postgres
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
su - -c "createuser -s ${POSTGRES_USER}" postgres
echo ""

echo "##################################################################"
# Unzip the backup archive
BACKUP_UNCOMPRESSED_NAME=$(basename ${BACKUP_NAME} .gz)
echo -e "\e[32mGunzipping the backup archive from ${BACKUPFOLDER}/${BACKUP_NAME} to /tmp/${BACKUP_UNCOMPRESSED_NAME}\e[0m"
echo gunzip -c ${BACKUPFOLDER}/${BACKUP_NAME} > /tmp/${BACKUP_UNCOMPRESSED_NAME}
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
gunzip -c ${BACKUPFOLDER}/${BACKUP_NAME} > /tmp/${BACKUP_UNCOMPRESSED_NAME}
chown postgres /tmp/${BACKUP_UNCOMPRESSED_NAME}
echo ""

echo "##################################################################"
# Restore the backup
echo -e "\e[32mRestoring the database from /tmp/${BACKUP_UNCOMPRESSED_NAME}\e[0m"
echo su - -c \"psql -U ${POSTGRES_USER} -d postgres -f /tmp/${BACKUP_UNCOMPRESSED_NAME}\" postgres
echo "Sleeping ${SLEEP_TIME} seconds..."
sleep $SLEEP_TIME
su - -c "psql -U ${POSTGRES_USER} -d postgres -f /tmp/${BACKUP_UNCOMPRESSED_NAME}" postgres
echo ""

echo ""
echo -e "\e[32mAll done.\e[0m"
