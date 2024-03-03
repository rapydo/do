FROM stilliard/pure-ftpd:buster-latest

RUN apt-get update -qq \
    && apt-get dist-upgrade --yes -qq \
    && apt-get autoremove --yes && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --chmod=740 ./ftp_utilities.sh /usr/local/bin/myftp

RUN echo "echo 'Use myftp command to create/modify users'" >> /root/.bashrc

# startup, also repeated into the docker-entrypoint
CMD ["/run.sh", "-c", "50", "-C", "10", "-l", "puredb:/etc/pure-ftpd/pureftpd.pdb", "-E", "-j", "-R", "-P", "$PUBLICHOST", "-p", "30000:30019"]

EXPOSE 21 30000-30019

COPY --chmod=740 reload-ftp.sh /usr/local/bin/reload
COPY banner.sh print_versions.sh /etc/
RUN echo '/bin/bash /etc/banner.sh' >> /etc/bash.bashrc

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]
