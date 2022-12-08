FROM adminer:4.8.1

USER root

RUN apk update --no-cache && \
    apk upgrade --no-cache && \
    apk add --no-cache nginx autoconf gcc g++ make libffi-dev openssl-dev

COPY --chmod=740 ./docker-entrypoint.sh /usr/local/bin/nginx-docker-entrypoint

COPY ./development.conf /etc/nginx/adminer-development.conf
COPY ./production.conf /etc/nginx/adminer-production.conf

RUN mkdir -p /run/nginx \
    && rm -f /etc/nginx/http.d/default.conf \
    && sed -i '3i/usr/local/bin/nginx-docker-entrypoint' /usr/local/bin/docker-php-entrypoint

EXPOSE 80

COPY --chmod=740 reload-adminer.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/ash /etc/banner.sh' >> ~/.bashrc
