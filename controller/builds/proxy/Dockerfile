FROM nginx:1.26.0-alpine as build-certbot

RUN apk update --no-cache && \
    apk add --no-cache gcc musl-dev libffi-dev python3-dev py3-pip

ENV CERTBOT_PATH="/opt/certbot"

RUN python3 -m venv "${CERTBOT_PATH}"

ENV PATH="${CERTBOT_PATH}/bin:$PATH"

RUN pip3 install --no-cache-dir certbot==2.11.0

FROM nginx:1.26.0-alpine

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION" && \
    mkdir -p /etc/rapydo && echo $RAPYDO_VERSION > /etc/rapydo/release

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"

ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

RUN apk update --no-cache && \
    apk upgrade --no-cache && \
    apk add --no-cache vim wget git bash openssl curl netcat-openbsd shadow tini python3

ENV CERTBOT_PATH="/opt/certbot"
COPY --from=build-certbot ${CERTBOT_PATH} ${CERTBOT_PATH}
ENV PATH="${CERTBOT_PATH}/bin:$PATH"

RUN mkdir -p /usr/share/nginx/html/.well-known
RUN chown -R nginx /usr/share/nginx/html

ENV WWWDIR /usr/share/nginx/html

ENV CERTDIR /etc/letsencrypt
ENV CERTSUBDIR real
ENV CERTKEYFILE $CERTSUBDIR/privkey1.pem
ENV CERTCHAINFILE $CERTSUBDIR/fullchain1.pem
ENV CERTKEY ${CERTDIR}/${CERTKEYFILE}
ENV CERTCHAIN ${CERTDIR}/${CERTCHAINFILE}
ENV DHPARAM /etc/letsencrypt/dhparam.pem

RUN mkdir -p $CERTDIR/$CERTSUBDIR

COPY nginx.conf /etc/nginx/nginx.conf
COPY confs /etc/nginx/sites-enabled-templates

COPY create_ssl_certificate.sh /usr/local/bin/updatecertificates
COPY maintenance.html /usr/share/nginx/html/maintenance.html
COPY 404.html /usr/share/nginx/html/custom_404.html
COPY 502.html /usr/share/nginx/html/custom_502.html
COPY 504.html /usr/share/nginx/html/custom_504.html
COPY errors.css /usr/share/nginx/html/errors.css
COPY giphy.gif /usr/share/nginx/html/giphy.gif
RUN chmod +r /usr/share/nginx/html/*

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint
COPY ./docker-entrypoint-maintenance.sh /usr/local/bin/docker-entrypoint-maintenanance

RUN groupmod -og $CURRENT_GID nginx && usermod -u $CURRENT_UID nginx

ENTRYPOINT ["/sbin/tini", "/usr/local/bin/docker-entrypoint"]
CMD ["proxy"]

COPY --chmod=740 reload-proxy.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/ash /etc/banner.sh' >> ~/.bashrc
