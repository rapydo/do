FROM postgres:16.2-alpine

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

# install usermod utility to change the user uid
RUN apk update --no-cache && apk upgrade --no-cache && apk add --no-cache shadow

COPY --chmod=555 ./pgs_init.sh /docker-entrypoint-initdb.d/setup-my-schema.sh
# permissions to others are required because postgres does not run with CURRENT_UID
# read to all
COPY --chmod=444 ./postgresql.conf /etc/postgresql/postgresql.conf
# read&exec to all
COPY --chmod=555 ./version_upgrade.sh /usr/local/bin/version_upgrade
COPY --chmod=555 ./check_datadir.sh /check_datadir.sh

# Adding my own script as second line of the original entrypoint
RUN sed -i '4ibash /check_datadir.sh' /usr/local/bin/docker-entrypoint.sh

RUN DATADIR=$(dirname "${PGDATA}") && mkdir -p "${DATADIR}"/"${PG_MAJOR}"

WORKDIR /var/lib/postgresql/

COPY --chmod=740 reload-postgres.sh /usr/local/bin/reload
COPY --chmod=444 banner.sh print_versions.sh /etc/
# /var/lib/postgresql is the home of the postgres as defined in
# https://github.com/docker-library/postgres/blob/master/13/alpine/Dockerfile
RUN echo '/bin/ash /etc/banner.sh' >> /var/lib/postgresql/.bashrc
