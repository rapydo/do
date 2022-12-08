#!/bin/bash

if [[ -f ${PGDATA}/postgresql.conf ]] && [[ ! -L ${PGDATA}/postgresql.conf ]]; then
    # Force postgresql.conf in datadir to be a link to the default conf file
    # Default conf file is copied into the container at build time
    # This will update newly-created datadirs.
    # A similar check in check_datadir.sh will ensure the link for already created datadirs
    ln -sf /etc/postgresql/postgresql.conf ${PGDATA}/postgresql.conf
fi
## http://www.postgresql.org/docs/9.1/static/auth-pg-hba-conf.html
net="0.0.0.0/0"

hba_conf='/var/lib/postgresql/current/pg_hba.conf'

echo "Changing access"
echo "" > $hba_conf

echo "local   all  all  trust" >> $hba_conf

echo "hostnossl       postgres  $POSTGRES_USER  $net   password" >> $hba_conf

###################
# DBs handling
for obj in $POSTGRES_DBS;
do
    db=$(echo $obj | tr -d "'")
    echo "Enabling DB $db"
# Create it
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" << EOSQL
    CREATE DATABASE "$db";
EOSQL
    # GRANT ALL PRIVILEGES ON DATABASE "$db" TO $POSTGRES_USER;
# Add privileges
echo "hostnossl       $db  $POSTGRES_USER  $net   password" >> $hba_conf
done

###################
echo "DONE"

## In case you need to startup a database

# echo "******CREATING DATABASE******"
# gosu postgres postgres --single << EOSQL
# CREATE USER docker WITH SUPERUSER PASSWORD 'test';
# #CREATE ROLE docker CREATEDB LOGIN PASSWORD 'test';
# # CREATE DATABASE docker;
# # CREATE USER docker WITH ENCRYPTED PASSWORD 'test';
# # GRANT ALL PRIVILEGES ON DATABASE docker to docker;
# EOSQL
