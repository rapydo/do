FROM registry:2.8.3

# apache2-utils adds htpasswd
RUN apk update --no-cache && apk upgrade --no-cache && apk add --no-cache openssl apache2-utils

COPY --chmod=5 ./set_security.sh /set_security.sh

# Adding my own script as 4th line of the original entrypoint
RUN sed -i '4iash /set_security.sh' /entrypoint.sh

COPY --chmod=740 reload-registry.sh /usr/local/bin/reload
