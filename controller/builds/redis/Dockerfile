FROM redis:7.2.3

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

RUN apt-get update -qq \
    && apt-get dist-upgrade --yes -qq \
    && apt-get autoremove --yes && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --chmod=740 reload-redis.sh /usr/local/bin/reload
COPY --chmod=740 ./fix_user.sh /fix_user.sh

RUN sed -i '3iif [ `id -u` -eq 0 ] ; then /fix_user.sh; fi' /usr/local/bin/docker-entrypoint.sh
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/bash /etc/banner.sh' >> /etc/bash.bashrc
