FROM node:20.11.1-buster
# https://nodejs.org/en/blog/release

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN groupmod -og $CURRENT_GID node && usermod -u $CURRENT_UID node

# used by print_versions
ENV ANGULAR_VERSION 15.2.10
ENV NODE_PATH /opt/node_modules
ENV CYPRESS_PATH /usr/local/Cypress
ENV CYPRESS_VERSION 13.7.1
ENV CYPRESS_RUN_BINARY=${CYPRESS_PATH}/${CYPRESS_VERSION}/Cypress/Cypress

# Install Chrome
# from libgtk2.0-0 to xvfb are required by cypress as reported here:
# https://docs.cypress.io/guides/guides/continuous-integration.html#Dependencies
# dbus-x11 is required by chrome
RUN \
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
  echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
  apt-get update -qq && \
  apt-get dist-upgrade --yes -qq && \
  apt-get install --yes --no-install-recommends vim libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb dbus-x11 google-chrome-stable && \
  apt-get autoremove --yes && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  google-chrome --version

RUN npm install -g npm yarn @angular/cli@${ANGULAR_VERSION} ts-json-schema-generator@1.5.0 sitemap-generator-cli@7.5.0 angular-spec-generator@1.1.0 cypress@${CYPRESS_VERSION} --force

# 777 is required to let node user to write the folder, even when uid is fixed at runtime.
RUN mv /root/.cache/Cypress /usr/local/Cypress && chown -R node:node /usr/local/Cypress && chmod -R 777 /usr/local/Cypress

RUN npm install --prefix /opt dotenv@16.4.5 deepmerge@4.3.1 ajv@8.12.0 ajv-formats@2.1.1

WORKDIR /app/

EXPOSE 8080

EXPOSE 9876

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint
COPY --chmod=777 ./reload-types.sh /usr/local/bin/reload-types
COPY --chmod=740 reload-angular.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/

RUN echo '/bin/bash /etc/banner.sh' >> /etc/bash.bashrc

CMD ["docker-entrypoint"]
