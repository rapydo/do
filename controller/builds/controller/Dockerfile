FROM docker:dind

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

RUN apk update --no-cache && \
    apk upgrade --no-cache && \
    apk add --no-cache python3 python3-dev py3-wheel py-pip git curl syslog-ng

RUN pip3 install --upgrade --no-cache-dir git+https://github.com/rapydo/do.git@$RAPYDO_VERSION#egg=rapydo[dev]

# Needed to make git commit (used by tests) to work and prevent error: 'Author identity unknown'
RUN git config --global user.email "tests@rapy.do" && git config --global user.name "RAPyDo"

RUN rapydo install buildx && rapydo install compose

# got with pip show rapydo | grep "Location:"
WORKDIR /usr/lib/python3.9/site-packages/controller
