FROM adminer:4.8.1

USER root

# RUN apk update --no-cache && \
#     apk upgrade --no-cache && \
#     apk add --no-cache nginx autoconf gcc g++ make libffi-dev openssl-dev

RUN apt-get update -qq \
     && apt-get dist-upgrade --yes -qq \
     && apt-get install --yes --no-install-recommends \
     nginx \
     && apt-get autoremove --yes && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --chmod=740 ./docker-entrypoint.sh /usr/local/bin/nginx-docker-entrypoint

COPY ./development.conf /etc/nginx/adminer-development.conf
COPY ./production.conf /etc/nginx/adminer-production.conf

RUN rm -f /etc/nginx/sites-enabled/default \
    && sed -i '3i/usr/local/bin/nginx-docker-entrypoint' /usr/local/bin/entrypoint.sh

EXPOSE 80

COPY --chmod=740 reload-adminer.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/bash /etc/banner.sh' >> ~/.bashrc
