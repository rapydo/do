FROM ubuntu:22.04

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"
ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

ENV PYTHON_VERSION 3.8

ENV TERM=xterm-256color
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
## for apt to be noninteractive
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true

## preesed tzdata, update package index, upgrade packages and install needed software
RUN echo "tzdata tzdata/Areas select Etc" > /tmp/preseed.txt; \
    echo "tzdata tzdata/Zones/Europe select UTC" >> /tmp/preseed.txt; \
    debconf-set-selections /tmp/preseed.txt \
    && apt-get update -qq \
    && apt-get dist-upgrade --yes -qq \
    && apt-get install --yes --no-install-recommends \
    tzdata bash file less vim curl wget telnet iputils-ping sysstat git zip unzip build-essential gosu cron ca-certificates libgeos-dev \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-dev \
    python3-gdbm python3-setuptools \
    && ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3 \
    && curl --silent https://bootstrap.pypa.io/get-pip.py --output get-pip.py \
    && python3 get-pip.py \
    && rm get-pip.py \
    && apt-get autoremove --yes && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade --no-cache-dir -r /tmp/requirements.txt \
  && pip3 install --upgrade --no-cache-dir git+https://github.com/rapydo/http-api.git@$RAPYDO_VERSION#egg=rapydo_http[dev]

ENV APIUSER developer

RUN useradd \
    -r -M -d /home/$APIUSER -s /bin/bash -p ! \
    --uid $CURRENT_UID $APIUSER \
    && groupmod -og $CURRENT_GID $APIUSER \
    && mkdir -p /home/$APIUSER \
    && chown $CURRENT_UID:$CURRENT_GID /home/$APIUSER

# GUNICORN
ENV GUNICORN_CONF /tmp/gunicorn_conf.py
COPY gunicorn_conf.py ${GUNICORN_CONF}
COPY --chmod=740 launch_gunicorn.sh /usr/local/bin/mygunicorn

# UTILITIES
COPY --chmod=740 flask_migrate /usr/local/bin/flask_migrate

# variables
ENV PAGER less
ENV PYTHONIOENCODING="utf-8"
ENV FLASK_PORT 8080
ENV CODE_DIR /code
ENV CERTDIR /opt/certificates
ENV PYTHONPATH $CODE_DIR

EXPOSE $FLASK_PORT

#### Make the terminal prettier ####
# generated with http://bashrcgenerator.com/
RUN echo 'export PS1="\\[\\033[38;5;11m\\]\\u\\[$(tput sgr0)\\]\\[\\033[38;5;15m\\]@\\h:\\[$(tput sgr0)\\]\\[\\033[38;5;6m\\][\\w]:\\[$(tput sgr0)\\]\\[\\033[38;5;15m\\] \\[$(tput sgr0)\\]"' >> /etc/bash.bashrc

# closing entrypoint

# RUN mkdir $CODE_DIR /docker-entrypoint.d/
RUN mkdir $CODE_DIR
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint
COPY ./docker-entrypoint-celery.sh /usr/local/bin/docker-entrypoint-celery

WORKDIR $CODE_DIR
ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
STOPSIGNAL SIGINT
CMD ["docker-entrypoint", "rest"]

RUN echo '/bin/bash /etc/banner.sh' >> /etc/bash.bashrc
COPY banner.sh print_versions.sh /etc/
COPY --chmod=740 reload-backend.sh /usr/local/bin/reload
COPY --chmod=740 celery-healthcheck.sh /usr/local/bin/celery-healthcheck
