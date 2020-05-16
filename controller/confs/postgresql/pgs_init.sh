#!/bin/bash

## http://www.postgresql.org/docs/9.1/static/auth-pg-hba-conf.html
net="0.0.0.0/0"

hba_conf='/var/lib/postgresql/data/pg_hba.conf'

echo "Changing access"
echo "" > $hba_conf

# Enable the user to perform health checks on localhost
echo "local   $POSTGRES_USER  $POSTGRES_USER  trust" >> $hba_conf

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
