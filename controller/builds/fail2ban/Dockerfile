FROM crazymax/fail2ban:1.1.0

RUN apk update --no-cache && apk upgrade --no-cache

COPY --chmod=740 reload-fail2ban.sh /usr/local/bin/reload
COPY --chmod=740 fix-configuration.sh /usr/local/bin/fix-configuration
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/ash /etc/banner.sh' >> ~/.bashrc

RUN sed -i '3i/usr/local/bin/fix-configuration' /entrypoint.sh
