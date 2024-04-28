FROM node:20.11.1-buster
# https://nodejs.org/en/blog/release

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

RUN apt-get update -qq \
    && apt-get dist-upgrade --yes -qq \
    && apt-get autoremove --yes && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupmod -og $CURRENT_GID node && usermod -u $CURRENT_UID node

ENV NODE_PATH /opt/node_modules
# used by print_versions
ENV ANGULAR_VERSION 17.3.6

RUN npm install -g npm yarn @angular/cli@${ANGULAR_VERSION} ts-json-schema-generator@1.5.1 sitemap-generator-cli@7.5.0 --force

RUN npm install --prefix /opt dotenv@16.4.5 deepmerge@4.3.1 ajv@8.12.0 ajv-formats@2.1.1

WORKDIR /app/

EXPOSE 8080

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint
COPY --chmod=777 ./reload-types.sh /usr/local/bin/reload-types

CMD ["docker-entrypoint"]

COPY --chmod=740 reload-angular.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/bash /etc/banner.sh' >> /etc/bash.bashrc
