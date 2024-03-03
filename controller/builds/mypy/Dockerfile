FROM python:3.11.3

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

RUN apt-get update -qq && \
    apt-get dist-upgrade --yes -qq && \
    apt-get install --yes --no-install-recommends libgeos-dev

RUN pip3 install --no-cache-dir git+https://github.com/rapydo/http-api.git@$RAPYDO_VERSION#egg=rapydo_http[types]

RUN mypy --version

# Super hack trick!! Since the default command for run --debug is bash
# and bash is not in alpine, let's abuse it to to be used as wrapper for mypy
COPY --chmod=740 run_mypy.sh /usr/local/bin/run_mypy
